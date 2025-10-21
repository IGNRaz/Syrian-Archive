from django.shortcuts import render
import os
import re
import html
import httpx
from bs4 import BeautifulSoup
from googlesearch import search as google_search
from deep_translator import GoogleTranslator
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
try:
    from archive_app.models import Post, PostVerification
except Exception:
    Post = None
    PostVerification = None


def _load_llm_config():
    env = os.environ
    provider = (env.get('LLM_PROVIDER') or '').strip().lower() or 'openai'

    def pick(*names):
        for n in names:
            v = env.get(n)
            if v:
                # Return trimmed value to avoid hidden whitespace issues
                return v.strip()
        return None

    # Prefer provider-specific key, then generic
    key = pick(f"{provider.upper()}_API_KEY", 'LLM_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY')
    if not key:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_root = os.path.dirname(base_dir)
            apikey_path = os.path.join(project_root, 'apikey')
            with open(apikey_path, 'r', encoding='utf-8') as f:
                key = f.read().strip()
        except Exception:
            key = None

    base_url = pick('LLM_BASE_URL', f"{provider.upper()}_BASE_URL", 'DEEPSEEK_BASE_URL')
    # Set safe defaults for known providers
    if not base_url and provider == 'deepseek':
        base_url = 'https://api.deepseek.com/v1'

    default_model = {'openai': 'gpt-4o-mini', 'deepseek': 'deepseek-chat'}.get(provider, 'gpt-4o-mini')
    model = pick('LLM_MODEL', f"{provider.upper()}_MODEL", 'OPENAI_MODEL', 'DEEPSEEK_MODEL') or default_model
    # Final trimming and normalization
    key = (key or '').strip() or None
    base_url = (base_url or '').strip() or None
    model = (model or '').strip() or default_model
    return key, provider, base_url, model


def investigator_home(request):
    llm_key, llm_provider, llm_base_url, llm_model = _load_llm_config()
    error = None
    internal_post = None
    internal_status = None
    # Quick mode skips AI summarization and only shows sources/internal status
    mode = request.GET.get('mode', '').strip().lower()
    quick_mode = mode == 'quick' or str(request.GET.get('quick', '')).strip().lower() in ('1', 'true', 'yes')
    # Recency filter: d (day), w (week), m (month), y (year), all (no limit)
    timelimit = (request.GET.get('time') or request.GET.get('timelimit') or '').strip().lower()
    if timelimit not in ('d', 'w', 'm', 'y', 'all'):
        timelimit = 'w'
    # Map to Google tbs param and a human label
    tbs_map = {'d': 'qdr:d', 'w': 'qdr:w', 'm': 'qdr:m', 'y': 'qdr:y'}
    if timelimit == 'all':
        tbs_param = None
        period_label = 'بدون تقييد زمني'
    else:
        tbs_param = tbs_map.get(timelimit, 'qdr:w')
        period_label_map = {'d': 'اليوم', 'w': 'الأسبوع', 'm': 'الشهر', 'y': 'السنة'}
        period_label = period_label_map.get(timelimit, 'الأسبوع')
    internal_verifications = {
        'journalist': 0,
        'politician': 0,
        'total': 0,
        'is_verified_flag': False,
    }

    # Use Arabic defaults and enforce Arabic response
    default_prompt = 'تكلّم عربي فقط. ابحث عن المواضيع المتعلقة بهذا الأمر وأن تكون متعلقة بسوريا.'
    prompt = request.GET.get('q', default_prompt)
    # "search_text" يمثل نص البحث الفعلي المبني من تفاصيل المنشور (العنوان + الوصف)
    search_text = None
    post_id = request.GET.get('post_id')
    # If post_id provided, load internal post and adapt prompt
    if post_id and Post:
        try:
            internal_post = get_object_or_404(Post, pk=int(post_id))
            # Build a focused prompt and search text from post title/content
            title_part = (internal_post.title or '').strip()
            content_full = (getattr(internal_post, 'content', '') or '')
            content_snippet = content_full.strip()[:800]
            # Prompt guides the model; search_text fuels web queries with details
            if title_part and content_snippet:
                prompt = f"تحقّق من صحة المنشور بعنوان: {title_part}. استخدم الوصف للتفاصيل."
                search_text = f"{title_part} — {content_snippet}"
            elif title_part:
                prompt = f"تحقّق من صحة المنشور بعنوان: {title_part}."
                search_text = title_part
            elif content_snippet:
                prompt = f"تحقّق من صحة المنشور: {content_snippet}."
                search_text = content_snippet
            # Gather internal verifications
            try:
                verifs = PostVerification.objects.filter(post=internal_post)
                for v in verifs:
                    if v.type == 'journalist_confirm':
                        internal_verifications['journalist'] += 1
                    elif v.type == 'politician_confirm':
                        internal_verifications['politician'] += 1
                internal_verifications['total'] = internal_verifications['journalist'] + internal_verifications['politician']
            except Exception:
                pass
            # is_verified flag if model has it
            try:
                internal_verifications['is_verified_flag'] = bool(getattr(internal_post, 'is_verified', False))
            except Exception:
                internal_verifications['is_verified_flag'] = False
            internal_status = {
                'exists': True,
                'title': internal_post.title,
                'is_verified': internal_verifications['is_verified_flag'],
                'journalist_count': internal_verifications['journalist'],
                'politician_count': internal_verifications['politician'],
                'total_verifications': internal_verifications['total'],
                # Provide snippet of original content for AI context (not UI)
                'content_snippet': content_snippet or ''
            }
        except Exception:
            internal_status = {'exists': False}
    # Fallback: if no post details, use the prompt as search text
    if not search_text:
        search_text = prompt

    # Perform web search (Arabic prioritized; English fallback if needed)
    results_ar = []
    results_en = []
    wiki_results_ar = []
    wiki_results_en = []
    verify_hits = []
    news_results = []
    try:
        query_general = f"{search_text} سوريا"
        query_wiki = f"{search_text} site:wikipedia.org"
        # General web search via googlesearch-python (advanced to get title/description)
        try:
            if tbs_param:
                for r in google_search(query_general, num_results=10, lang='ar', region='sy', advanced=True, unique=True, tbs=tbs_param):
                    results_ar.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
            else:
                for r in google_search(query_general, num_results=10, lang='ar', region='sy', advanced=True, unique=True):
                    results_ar.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
        except Exception:
            pass
        # Always fetch English/global as a fallback pool
        try:
            query_general_en = f"{search_text} Syria"
            if tbs_param:
                for r in google_search(query_general_en, num_results=10, lang='en', region='us', advanced=True, unique=True, tbs=tbs_param):
                    results_en.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
            else:
                for r in google_search(query_general_en, num_results=10, lang='en', region='us', advanced=True, unique=True):
                    results_en.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
        except Exception:
            pass
        # Wikipedia search (do not apply strict time filters)
        try:
            for r in google_search(query_wiki, num_results=6, lang='ar', region='sy', advanced=True, unique=True):
                wiki_results_ar.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
        except Exception:
            pass
        query_wiki_alt = f"{search_text} سوريا site:wikipedia.org"
        try:
            for r in google_search(query_wiki_alt, num_results=6, lang='en', region='us', advanced=True, unique=True):
                wiki_results_en.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
        except Exception:
            pass
        # Journalism/fact-check verification search
        verify_query = (
            f"{search_text} تحقق صحفي OR fact-check OR تحقق الخبر site:reuters.com OR site:bbc.co.uk OR "
            f"site:afp.com OR site:apnews.com OR site:snopes.com OR site:politifact.com OR site:factcheck.org"
        )
        try:
            if tbs_param:
                for r in google_search(verify_query, num_results=8, lang='ar', region='sy', advanced=True, unique=True, tbs=tbs_param):
                    verify_hits.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
            else:
                for r in google_search(verify_query, num_results=8, lang='ar', region='sy', advanced=True, unique=True):
                    verify_hits.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
        except Exception:
            pass
        if not verify_hits:
            try:
                if tbs_param:
                    for r in google_search(verify_query, num_results=8, lang='en', region='us', advanced=True, unique=True, tbs=tbs_param):
                        verify_hits.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
                else:
                    for r in google_search(verify_query, num_results=8, lang='en', region='us', advanced=True, unique=True):
                        verify_hits.append({'title': getattr(r, 'title', None), 'href': getattr(r, 'url', None), 'body': getattr(r, 'description', None)})
            except Exception:
                pass
        # Recent news via Google News RSS; filter by timelimit
        try:
            import urllib.parse
            q_enc = urllib.parse.quote(query_general)
            # Arabic UI and Syria locale
            rss_url = f"https://news.google.com/rss/search?q={q_enc}&hl=ar&gl=SY&ceid=SY:ar"
            rss_resp = httpx.get(rss_url, timeout=20)
            rss_soup = BeautifulSoup(rss_resp.text, 'xml')
            items = rss_soup.find_all('item')
            from datetime import datetime, timedelta
            days_map = {'d': 1, 'w': 7, 'm': 30, 'y': 365}
            max_age_days = days_map.get(timelimit)
            cutoff = None
            if max_age_days:
                cutoff = datetime.utcnow() - timedelta(days=max_age_days)
            for it in items[:20]:
                title = it.title.text if it.title else None
                link = it.link.text if it.link else None
                pub = it.pubDate.text if it.pubDate else None
                date_val = None
                try:
                    # Example format: Tue, 24 Sep 2024 10:30:00 GMT
                    date_val = datetime.strptime(pub, '%a, %d %b %Y %H:%M:%S %Z') if pub else None
                except Exception:
                    date_val = None
                # Filter by cutoff if date known and cutoff is set
                if cutoff and date_val and date_val < cutoff:
                    continue
                desc = it.description.text if it.description else ''
                news_results.append({'title': title, 'href': link, 'body': desc, 'date': pub})
        except Exception:
            pass
        # Fallback: global English feed if Arabic feed empty
        if not news_results:
            try:
                import urllib.parse
                q_enc = urllib.parse.quote(f"{prompt} Syria")
                rss_url = f"https://news.google.com/rss/search?q={q_enc}&hl=en&gl=US&ceid=US:en"
                rss_resp = httpx.get(rss_url, timeout=20)
                rss_soup = BeautifulSoup(rss_resp.text, 'xml')
                items = rss_soup.find_all('item')
                for it in items[:20]:
                    title = it.title.text if it.title else None
                    link = it.link.text if it.link else None
                    pub = it.pubDate.text if it.pubDate else None
                    desc = it.description.text if it.description else ''
                    news_results.append({'title': title, 'href': link, 'body': desc, 'date': pub})
            except Exception:
                pass
    except Exception as e:
        error = f"Search error: {e}"

    # Helpers for summaries and Arabic detection
    def has_arabic(text):
        try:
            if not text:
                return False
            return any('\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F' for ch in text)
        except Exception:
            return False

    def make_summary(text, max_chars=280):
        if not text:
            return ''
        txt = ' '.join(text.strip().split())
        # Take up to ~2 sentences heuristically
        for sep in ['. ', '؟ ', '! ', '\n']:
            parts = txt.split(sep)
            if len(parts) > 1:
                candidate = (parts[0] + ' ' + parts[1]).strip()
                return candidate[:max_chars]
        return txt[:max_chars]

    translator = GoogleTranslator(source='auto', target='ar')

    # Fetch and extract text content; build summaries
    sources = []
    client_http = httpx.Client(timeout=10, follow_redirects=True)
    def extract_text(url):
        try:
            resp = client_http.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
                'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            });
            soup = BeautifulSoup(resp.text, 'lxml')
            # Remove script/style and nav
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = ' '.join(t.strip() for t in soup.get_text(separator=' ').split())
            return text[:8000]  # cap size
        except Exception:
            return ''

    # Build Arabic-first general sources, then fill to top 5 with English
    combined_general = []
    for r in results_ar:
        url = r.get('href')
        if not url:
            continue
        text = extract_text(url)
        base_summary = make_summary(text or (r.get('body') or ''))
        summary_ar = base_summary if has_arabic(base_summary) else (translator.translate(base_summary) if base_summary else '')
        combined_general.append({'title': r.get('title'), 'url': url, 'snippet': (r.get('body') or '')[:300], 'content': text, 'summary': summary_ar})
    if len(combined_general) < 5:
        for r in results_en:
            url = r.get('href')
            if not url:
                continue
            text = extract_text(url)
            base_summary = make_summary(text or (r.get('body') or ''))
            summary_ar = translator.translate(base_summary) if base_summary else ''
            combined_general.append({'title': r.get('title'), 'url': url, 'snippet': (r.get('body') or '')[:300], 'content': text, 'summary': summary_ar})
            if len(combined_general) >= 5:
                break
    sources = combined_general[:5]

    # Wikipedia sources (up to 3; Arabic first, English fallback)
    wiki_sources = []
    for r in wiki_results_ar:
        url = r.get('href')
        if not url:
            continue
        text = extract_text(url)
        base_summary = make_summary(text or (r.get('body') or ''))
        summary_ar = base_summary if has_arabic(base_summary) else (translator.translate(base_summary) if base_summary else '')
        wiki_sources.append({'title': r.get('title'), 'url': url, 'snippet': (r.get('body') or '')[:300], 'content': text, 'summary': summary_ar})
    if len(wiki_sources) < 3:
        for r in wiki_results_en:
            url = r.get('href')
            if not url:
                continue
            text = extract_text(url)
            base_summary = make_summary(text or (r.get('body') or ''))
            summary_ar = translator.translate(base_summary) if base_summary else ''
            wiki_sources.append({'title': r.get('title'), 'url': url, 'snippet': (r.get('body') or '')[:300], 'content': text, 'summary': summary_ar})
            if len(wiki_sources) >= 3:
                break
    wiki_sources = wiki_sources[:3]
    # News sources (top 5; include short summaries)
    news_sources = []
    for r in news_results:
        url = r.get('href')
        if not url:
            continue
        text = extract_text(url)
        base_summary = make_summary(text or (r.get('body') or ''))
        summary_ar = base_summary if has_arabic(base_summary) else (translator.translate(base_summary) if base_summary else '')
        news_sources.append({'title': r.get('title'), 'url': url, 'snippet': (r.get('body') or '')[:300], 'content': text, 'date': r.get('date'), 'summary': summary_ar})
    news_sources = news_sources[:5]

    # تحديث الرئيس الحالي من ويكيبيديا أو مصدر رسمي قبل إرسال الرسالة للـ LLM
    def get_current_president():
        try:
            wiki_url = "https://ar.wikipedia.org/wiki/رئيس_سوريا"
            resp = httpx.get(wiki_url, timeout=10)
            soup = BeautifulSoup(resp.text, 'lxml')
            # البحث عن السطر الذي يحتوي الرئيس الحالي داخل صندوق المعلومات
            infobox = soup.find("table", {"class": "infobox"})
            if infobox:
                rows = infobox.find_all("tr")
                for row in rows:
                    th = row.find("th")
                    td = row.find("td")
                    th_text = th.get_text(strip=True) if th else ''
                    if th and td and ("الرئيس الحالي" in th_text or "شاغل المنصب" in th_text):
                        return td.get_text(strip=True)
            return None
        except Exception:
            return None

    current_president = get_current_president()
    if current_president:
        # نضيفها للـ prompt بحيث الموديل يعرف الحقيقة الحديثة
        prompt = f"{prompt}\nملاحظة: الرئيس الحالي لسوريا وفق المصادر الرسمية هو {current_president}."

    # Summarize and cite using OpenAI in Arabic only (skip in quick mode)
    ai_response = None
    if not quick_mode:
        try:
            from openai import OpenAI
            if not llm_key:
                raise RuntimeError('LLM API key not found')
            # Use a custom HTTP client to avoid deprecated/removed proxies argument issues
            http_client = httpx.Client(timeout=60, trust_env=False)
            client = OpenAI(api_key=llm_key, http_client=http_client, base_url=llm_base_url) if llm_base_url else OpenAI(api_key=llm_key, http_client=http_client)
            # Prepare contexts
            context_general = []
            for s in sources[:5]:
                short = s.get('summary') or ''
                context_general.append(f"[مصدر عام] {s['title']} — {s['url']}\nملخص قصير: {short}\n---\n{s['content'][:2000]}")
            context_wiki = []
            for s in wiki_sources[:3]:
                short = s.get('summary') or ''
                context_wiki.append(f"[ويكيبيديا] {s['title']} — {s['url']}\nملخص قصير: {short}\n---\n{s['content'][:2000]}")
            context_news = []
            for s in news_sources[:5]:
                date = s.get('date') or 'غير معروف'
                short = s.get('summary') or ''
                context_news.append(f"[أخبار حديثة] {s['title']} — {s['url']} — التاريخ: {date}\nملخص قصير: {short}\n---\n{s['content'][:2000]}")
            context_verify = []
            for v in verify_hits[:5]:
                context_verify.append(f"[تحقق صحفي] {v['title']} — {v['href']}\n---\n{(v.get('body') or '')[:400]}")

            system_prompt = (
                "أنت محقّق سوري. تحدث بالعربية الفصحى فقط. مهمتك التحقق من صحة الادعاءات أو المنشورات المتعلقة بسوريا. استخدم الخطوات التالية:\n\n"
                "1. قيم صحة المنشور أو الادعاء وحدد الحكم النهائي: صحيح / زائف / غير مؤكد.\n"
                "2. اعتمد على مصادر ويب موثوقة وحديثة، مع إعطاء الأولوية للتقارير الأخيرة وفق الفترة الزمنية المحددة (اليوم/الأسبوع/الشهر/السنة).\n"
                "3. استشهد بالمصادر مع ذكر الرابط والتاريخ إن أمكن.\n"
                "4. ضع أدلة وملاحظات مختصرة وواضحة تشرح سبب الحكم.\n"
                "5. إذا كانت الأدلة غير كافية، أشر صراحة أن الحكم غير مؤكد.\n"
                "6. لا تستخدم أي لغة أخرى غير العربية.\n"
                "7. ركّز على سوريا فقط، وتجنب النتائج العامة غير المتعلقة بالموضوع.\n"
                "8. قيّم الادعاءات استنادًا إلى عنوان ووصف المنشور الأصلي المرفق ضمن السياق.\n\n"
                "الرجاء تقديم ملخص منظم يشمل: الحكم النهائي، الأدلة، الملاحظات، وروابط المصادر."
            )
            internal_context = ''
            if internal_status and internal_status.get('exists'):
                internal_context = (
                    f"[حالة داخلية للمنشور]\n"
                    f"العنوان: {internal_status.get('title') or 'غير متوفر'}\n"
                    f"موثّق في النظام: {'نعم' if internal_status.get('is_verified') else 'لا'}\n"
                    f"عدد التحقّق الصحفي: {internal_status.get('journalist_count')}\n"
                    f"عدد تأكيد السياسيين: {internal_status.get('politician_count')}\n"
                    f"إجمالي التحقّقات: {internal_status.get('total_verifications')}\n"
                    f"النص الأصلي (مقتطف): {internal_status.get('content_snippet') or 'غير متوفر'}\n"
                )
            user_msg = (
                f"السؤال:\n{prompt}\n\n"
                f"{internal_context}\n"
                f"الفترة الزمنية للبحث: {period_label} ({timelimit})\n\n"
                f"مصادر ويب عامة:\n{'\n\n'.join(context_general) or 'لا توجد'}\n\n"
                f"مصادر ويكيبيديا:\n{'\n\n'.join(context_wiki) or 'لا توجد'}\n\n"
                f"مصادر الأخبار الحديثة:\n{'\n\n'.join(context_news) or 'لا توجد'}\n\n"
                f"مصادر تحقق صحفي:\n{'\n\n'.join(context_verify) or 'لا توجد'}\n\n"
                "الرجاء: أعطني خلاصة عربية منظّمة تشمل: الحكم النهائي (صحيح/زائف/غير مؤكد)،"
                " الأدلة والملاحظات، والروابط المستخدمة مع ذكر التاريخ لكل مصدر إن أمكن."
            )
            completion = client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            ai_response = completion.choices[0].message.content
        except Exception as e:
            error = f"AI error: {e}"

    return render(request, 'the_syrian_investigator/home.html', {
        'prompt': prompt,
        'ai_response': ai_response,
        'error': error,
        'sources': sources,
        'wiki_sources': wiki_sources,
        'news_sources': news_sources,
        'verify_hits': verify_hits,
        'post_id': post_id or '',
        'internal_status': internal_status,
        'timelimit': timelimit,
        'period_label': period_label,
    })


# Create your views here.
