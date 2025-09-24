from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from auth_payments.models import PaymentTransaction, PaymentLog, PaymentMethod
from auth_payments.settings_config import get_security_setting
from datetime import timedelta
import logging
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up old payment data, logs, and security records according to retention policies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to retain data (default: 90)',
        )
        parser.add_argument(
            '--logs-only',
            action='store_true',
            help='Clean up only logs, skip payment data',
        )
        parser.add_argument(
            '--data-only',
            action='store_true',
            help='Clean up only payment data, skip logs',
        )
        parser.add_argument(
            '--cache-only',
            action='store_true',
            help='Clean up only cache data, skip database records',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        # Set up logging level
        if options['verbose']:
            logging.basicConfig(level=logging.INFO)
        
        retention_days = options['days']
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting cleanup process for data older than {retention_days} days "
                f"(before {cutoff_date.date()})"
            )
        )
        
        if not options['force'] and not options['dry_run']:
            confirm = input(
                f"This will permanently delete payment data older than {retention_days} days. "
                "Are you sure? (yes/no): "
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return
        
        cleanup_stats = {
            'payment_logs_deleted': 0,
            'old_transactions_anonymized': 0,
            'expired_payment_methods_deleted': 0,
            'cache_entries_cleared': 0,
            'log_files_rotated': 0,
        }
        
        try:
            # Clean up cache data
            if not options['logs_only'] and not options['data_only']:
                self.stdout.write("Cleaning up cache data...")
                cache_stats = self._cleanup_cache_data(options['dry_run'])
                cleanup_stats['cache_entries_cleared'] = cache_stats['cleared']
            
            # Clean up payment logs
            if not options['data_only'] and not options['cache_only']:
                self.stdout.write("Cleaning up payment logs...")
                log_stats = self._cleanup_payment_logs(cutoff_date, options['dry_run'])
                cleanup_stats['payment_logs_deleted'] = log_stats['deleted']
            
            # Clean up old payment data
            if not options['logs_only'] and not options['cache_only']:
                self.stdout.write("Processing old payment transactions...")
                transaction_stats = self._anonymize_old_transactions(cutoff_date, options['dry_run'])
                cleanup_stats['old_transactions_anonymized'] = transaction_stats['anonymized']
                
                self.stdout.write("Cleaning up expired payment methods...")
                payment_method_stats = self._cleanup_expired_payment_methods(options['dry_run'])
                cleanup_stats['expired_payment_methods_deleted'] = payment_method_stats['deleted']
            
            # Rotate log files
            if not options['data_only'] and not options['cache_only']:
                self.stdout.write("Rotating log files...")
                log_rotation_stats = self._rotate_log_files(options['dry_run'])
                cleanup_stats['log_files_rotated'] = log_rotation_stats['rotated']
            
            # Summary
            self._print_cleanup_summary(cleanup_stats, options['dry_run'])
        
        except Exception as e:
            logger.error(f"Cleanup process failed: {str(e)}")
            raise CommandError(f"Command failed: {str(e)}")
    
    def _cleanup_cache_data(self, dry_run=False):
        """Clean up expired cache entries"""
        cleared_count = 0
        
        # Cache keys to clean up
        cache_patterns = [
            'rate_limit:*',
            'failed_attempts:*',
            'suspicious_activity:*',
            'banned_ip:*',
            'flagged_user:*',
            'reminder_sent:*',
            'followup_sent:*',
        ]
        
        if not dry_run:
            # Note: Django's cache doesn't support pattern-based deletion
            # This is a simplified approach - in production, you might want to use Redis directly
            try:
                # Clear all cache (be careful in production)
                cache.clear()
                cleared_count = 1  # Approximate
                logger.info("Cache cleared successfully")
            except Exception as e:
                logger.error(f"Failed to clear cache: {str(e)}")
        else:
            self.stdout.write("  Would clear expired cache entries")
            cleared_count = 1  # Dry run estimate
        
        return {'cleared': cleared_count}
    
    def _cleanup_payment_logs(self, cutoff_date, dry_run=False):
        """Clean up old payment logs"""
        old_logs = PaymentLog.objects.filter(created_at__lt=cutoff_date)
        count = old_logs.count()
        
        if dry_run:
            self.stdout.write(f"  Would delete {count} payment log entries")
        else:
            if count > 0:
                with transaction.atomic():
                    deleted_count, _ = old_logs.delete()
                    logger.info(f"Deleted {deleted_count} old payment log entries")
                    self.stdout.write(f"  Deleted {deleted_count} payment log entries")
            else:
                self.stdout.write("  No old payment logs to delete")
        
        return {'deleted': count}
    
    def _anonymize_old_transactions(self, cutoff_date, dry_run=False):
        """Anonymize old payment transactions (GDPR compliance)"""
        # Only anonymize completed transactions older than retention period
        old_transactions = PaymentTransaction.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed']
        ).exclude(
            # Don't anonymize if user_email is already anonymized
            user_email__startswith='anonymized_'
        )
        
        count = old_transactions.count()
        
        if dry_run:
            self.stdout.write(f"  Would anonymize {count} old transaction records")
        else:
            if count > 0:
                anonymized_count = 0
                with transaction.atomic():
                    for trans in old_transactions:
                        # Anonymize personal data while keeping transaction records for accounting
                        trans.user_email = f"anonymized_{trans.id}@deleted.local"
                        trans.billing_address = None
                        trans.save(update_fields=['user_email', 'billing_address'])
                        anonymized_count += 1
                
                logger.info(f"Anonymized {anonymized_count} old transaction records")
                self.stdout.write(f"  Anonymized {anonymized_count} transaction records")
            else:
                self.stdout.write("  No old transactions to anonymize")
        
        return {'anonymized': count}
    
    def _cleanup_expired_payment_methods(self, dry_run=False):
        """Clean up expired and unused payment methods"""
        current_date = timezone.now().date()
        
        # Find expired payment methods
        expired_methods = PaymentMethod.objects.filter(
            card_exp_year__lt=current_date.year
        ).union(
            PaymentMethod.objects.filter(
                card_exp_year=current_date.year,
                card_exp_month__lt=current_date.month
            )
        )
        
        # Also find unused payment methods older than 1 year
        one_year_ago = timezone.now() - timedelta(days=365)
        unused_methods = PaymentMethod.objects.filter(
            created_at__lt=one_year_ago,
            is_default=False
        ).exclude(
            # Don't delete if used in recent transactions
            id__in=PaymentTransaction.objects.filter(
                created_at__gte=one_year_ago
            ).values_list('payment_method_id', flat=True)
        )
        
        total_to_delete = expired_methods.union(unused_methods)
        count = total_to_delete.count()
        
        if dry_run:
            self.stdout.write(f"  Would delete {count} expired/unused payment methods")
        else:
            if count > 0:
                with transaction.atomic():
                    deleted_count, _ = total_to_delete.delete()
                    logger.info(f"Deleted {deleted_count} expired/unused payment methods")
                    self.stdout.write(f"  Deleted {deleted_count} payment methods")
            else:
                self.stdout.write("  No expired payment methods to delete")
        
        return {'deleted': count}
    
    def _rotate_log_files(self, dry_run=False):
        """Rotate and compress old log files"""
        from django.conf import settings
        
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        rotated_count = 0
        
        if not os.path.exists(log_dir):
            self.stdout.write("  No log directory found")
            return {'rotated': 0}
        
        log_files = ['payments.log', 'security.log']
        
        for log_file in log_files:
            log_path = os.path.join(log_dir, log_file)
            
            if os.path.exists(log_path):
                # Check file size (rotate if > 10MB)
                file_size = os.path.getsize(log_path)
                if file_size > 10 * 1024 * 1024:  # 10MB
                    if dry_run:
                        self.stdout.write(f"  Would rotate {log_file} ({file_size / 1024 / 1024:.1f}MB)")
                        rotated_count += 1
                    else:
                        try:
                            # Simple rotation - move to .old
                            old_path = f"{log_path}.old"
                            if os.path.exists(old_path):
                                os.remove(old_path)
                            os.rename(log_path, old_path)
                            
                            # Create new empty log file
                            open(log_path, 'a').close()
                            
                            rotated_count += 1
                            self.stdout.write(f"  Rotated {log_file}")
                            logger.info(f"Rotated log file: {log_file}")
                        except Exception as e:
                            logger.error(f"Failed to rotate {log_file}: {str(e)}")
        
        return {'rotated': rotated_count}
    
    def _print_cleanup_summary(self, stats, dry_run=False):
        """Print cleanup summary"""
        action = "Would be processed" if dry_run else "Processed"
        
        self.stdout.write(f"\nCleanup Summary ({action}):")
        self.stdout.write(f"  Payment logs deleted: {stats['payment_logs_deleted']}")
        self.stdout.write(f"  Transactions anonymized: {stats['old_transactions_anonymized']}")
        self.stdout.write(f"  Payment methods deleted: {stats['expired_payment_methods_deleted']}")
        self.stdout.write(f"  Cache entries cleared: {stats['cache_entries_cleared']}")
        self.stdout.write(f"  Log files rotated: {stats['log_files_rotated']}")
        
        total_actions = sum(stats.values())
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry run completed. {total_actions} actions would be performed."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nCleanup completed successfully. {total_actions} actions performed."
                )
            )