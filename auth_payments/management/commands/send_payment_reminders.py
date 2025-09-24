from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from auth_payments.notifications import NotificationScheduler
from auth_payments.models import Subscription, PaymentTransaction
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send payment reminders and follow-up notifications for subscriptions and failed payments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reminders-only',
            action='store_true',
            help='Send only payment reminders, skip failed payment follow-ups',
        )
        parser.add_argument(
            '--followups-only',
            action='store_true',
            help='Send only failed payment follow-ups, skip payment reminders',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        scheduler = NotificationScheduler()
        
        # Set up logging level
        if options['verbose']:
            logging.basicConfig(level=logging.INFO)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting payment notification processing at {timezone.now()}"
            )
        )
        
        total_results = {
            'reminders_sent': 0,
            'reminders_failed': 0,
            'reminders_skipped': 0,
            'followups_sent': 0,
            'followups_failed': 0,
            'followups_skipped': 0,
        }
        
        try:
            # Send payment reminders
            if not options['followups_only']:
                self.stdout.write("Processing payment reminders...")
                
                if options['dry_run']:
                    reminder_stats = self._dry_run_reminders()
                else:
                    reminder_results = scheduler.send_payment_reminders()
                    total_results['reminders_sent'] = reminder_results['sent']
                    total_results['reminders_failed'] = reminder_results['failed']
                    total_results['reminders_skipped'] = reminder_results['skipped']
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Payment reminders: {total_results['reminders_sent']} sent, "
                        f"{total_results['reminders_failed']} failed, "
                        f"{total_results['reminders_skipped']} skipped"
                    )
                )
            
            # Send failed payment follow-ups
            if not options['reminders_only']:
                self.stdout.write("Processing failed payment follow-ups...")
                
                if options['dry_run']:
                    followup_stats = self._dry_run_followups()
                else:
                    followup_results = scheduler.send_failed_payment_followups()
                    total_results['followups_sent'] = followup_results['sent']
                    total_results['followups_failed'] = followup_results['failed']
                    total_results['followups_skipped'] = followup_results['skipped']
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Failed payment follow-ups: {total_results['followups_sent']} sent, "
                        f"{total_results['followups_failed']} failed, "
                        f"{total_results['followups_skipped']} skipped"
                    )
                )
            
            # Summary
            total_sent = total_results['reminders_sent'] + total_results['followups_sent']
            total_failed = total_results['reminders_failed'] + total_results['followups_failed']
            total_skipped = total_results['reminders_skipped'] + total_results['followups_skipped']
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSummary: {total_sent} notifications sent, "
                    f"{total_failed} failed, {total_skipped} skipped"
                )
            )
            
            if total_failed > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Warning: {total_failed} notifications failed to send. "
                        "Check logs for details."
                    )
                )
        
        except Exception as e:
            logger.error(f"Payment notification processing failed: {str(e)}")
            raise CommandError(f"Command failed: {str(e)}")
    
    def _dry_run_reminders(self):
        """Show what reminders would be sent without actually sending them"""
        reminder_dates = [7, 3, 1]  # Days before renewal
        total_count = 0
        
        for days_ahead in reminder_dates:
            target_date = timezone.now().date() + timedelta(days=days_ahead)
            
            subscriptions = Subscription.objects.filter(
                status='active',
                current_period_end__date=target_date
            ).select_related('user')
            
            count = subscriptions.count()
            total_count += count
            
            self.stdout.write(
                f"  Would send {count} reminders for renewals in {days_ahead} days"
            )
            
            if count > 0 and self.verbosity >= 2:
                for sub in subscriptions:
                    self.stdout.write(
                        f"    - {sub.user.email} ({sub.plan_type} plan, ${sub.amount})"
                    )
        
        self.stdout.write(f"Total reminders that would be sent: {total_count}")
        return {'total': total_count}
    
    def _dry_run_followups(self):
        """Show what follow-ups would be sent without actually sending them"""
        week_ago = timezone.now() - timedelta(days=7)
        
        failed_transactions = PaymentTransaction.objects.filter(
            status='failed',
            created_at__gte=week_ago
        ).select_related('user', 'subscription')
        
        count = failed_transactions.count()
        
        self.stdout.write(
            f"  Would send {count} follow-ups for failed payments"
        )
        
        if count > 0 and self.verbosity >= 2:
            for transaction in failed_transactions:
                self.stdout.write(
                    f"    - {transaction.user.email} (${transaction.amount}, "
                    f"failed on {transaction.created_at.date()})"
                )
        
        self.stdout.write(f"Total follow-ups that would be sent: {count}")
        return {'total': count}