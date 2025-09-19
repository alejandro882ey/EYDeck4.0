"""
Django management command to validate and fix diferencial_mtd values.
Usage: python manage.py validate_diferencial_mtd
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum
from core_dashboard.models import RevenueEntry
from core_dashboard.utils import get_fiscal_month_year


class Command(BaseCommand):
    help = 'Validate and fix diferencial_mtd values for all fiscal months'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            help='Specific date to validate (YYYY-MM-DD format)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_date = options['date']
        
        if specific_date:
            try:
                from datetime import datetime
                target_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
                unique_dates = [target_date]
                if not RevenueEntry.objects.filter(date=target_date).exists():
                    self.stdout.write(
                        self.style.ERROR(f'No data found for date {target_date}')
                    )
                    return
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return
        else:
            # Get all unique dates
            unique_dates = RevenueEntry.objects.values_list('date', flat=True).distinct().order_by('date')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        total_fixes = 0
        
        for report_date in unique_dates:
            entries = RevenueEntry.objects.filter(date=report_date)
            
            # Get fiscal period information
            fiscal_period = get_fiscal_month_year(report_date)
            fiscal_month_name = fiscal_period.split(' ')[0]
            is_first_fiscal_month = fiscal_month_name == 'Julio'
            
            self.stdout.write(f"\nProcessing {report_date} (Fiscal Period: {fiscal_period})")
            
            if is_first_fiscal_month:
                self.stdout.write("  First fiscal month - validating diferencial_mtd = fytd_diferencial_final")
                
                # For first month, diferencial_mtd should equal fytd_diferencial_final
                # or both should be null/0
                
                entries_to_fix = []
                for entry in entries:
                    if entry.fytd_diferencial_final is not None:
                        if entry.diferencial_mtd != entry.fytd_diferencial_final:
                            entries_to_fix.append((entry, 'set_to_final', entry.fytd_diferencial_final))
                    elif entry.diferencial_mtd is not None and entry.diferencial_mtd != 0:
                        # If no fytd_diferencial_final but has diferencial_mtd, set to 0
                        entries_to_fix.append((entry, 'set_to_zero', 0))
                
                if entries_to_fix:
                    self.stdout.write(f"    Found {len(entries_to_fix)} entries to fix")
                    
                    if not dry_run:
                        for entry, action, new_value in entries_to_fix:
                            entry.diferencial_mtd = new_value
                            entry.save()
                        total_fixes += len(entries_to_fix)
                        self.stdout.write(self.style.SUCCESS(f"    Fixed {len(entries_to_fix)} entries"))
                    else:
                        for entry, action, new_value in entries_to_fix[:5]:  # Show first 5 examples
                            self.stdout.write(f"      Would fix ID {entry.id}: {action} -> {new_value}")
                        if len(entries_to_fix) > 5:
                            self.stdout.write(f"      ... and {len(entries_to_fix) - 5} more")
                else:
                    self.stdout.write("    No fixes needed")
            else:
                # For subsequent fiscal months, validate MTD calculation against fiscal calendar
                self.stdout.write("  Subsequent fiscal month - validating MTD calculation using fiscal calendar")
                
                # Find the last report from the previous fiscal month
                all_dates = RevenueEntry.objects.values_list('date', flat=True).distinct().order_by('date')
                
                last_report_prev_fiscal_month = None
                for date_entry in all_dates:
                    if date_entry >= report_date:
                        break
                    date_fiscal_period = get_fiscal_month_year(date_entry)
                    if date_fiscal_period != fiscal_period:
                        last_report_prev_fiscal_month = date_entry
                
                if last_report_prev_fiscal_month:
                    self.stdout.write(f"    Using {last_report_prev_fiscal_month} as baseline from previous fiscal month")
                    
                    # Get baseline data
                    baseline_entries = RevenueEntry.objects.filter(
                        date=last_report_prev_fiscal_month
                    ).values('engagement_id', 'fytd_diferencial_final')
                    
                    baseline_dict = {
                        entry['engagement_id']: entry['fytd_diferencial_final'] or 0
                        for entry in baseline_entries
                    }
                    
                    # Validate MTD calculations
                    entries_to_fix = []
                    for entry in entries:
                        if entry.fytd_diferencial_final is not None:
                            expected_mtd = entry.fytd_diferencial_final - baseline_dict.get(entry.engagement_id, 0)
                            if abs((entry.diferencial_mtd or 0) - expected_mtd) > 0.01:
                                entries_to_fix.append((entry, 'recalculate_mtd', expected_mtd))
                    
                    if entries_to_fix:
                        self.stdout.write(f"    Found {len(entries_to_fix)} entries with incorrect MTD calculation")
                        
                        if not dry_run:
                            for entry, action, new_value in entries_to_fix:
                                entry.diferencial_mtd = new_value
                                entry.save()
                            total_fixes += len(entries_to_fix)
                            self.stdout.write(self.style.SUCCESS(f"    Fixed {len(entries_to_fix)} entries"))
                        else:
                            for entry, action, new_value in entries_to_fix[:5]:
                                self.stdout.write(f"      Would fix ID {entry.id}: MTD {entry.diferencial_mtd} -> {new_value}")
                            if len(entries_to_fix) > 5:
                                self.stdout.write(f"      ... and {len(entries_to_fix) - 5} more")
                    else:
                        self.stdout.write("    MTD calculations are correct")
                else:
                    self.stdout.write("    No previous fiscal month data found for validation")
            
            # Calculate sums for verification
            total_diferencial_mtd = entries.aggregate(Sum('diferencial_mtd'))['diferencial_mtd__sum'] or 0
            total_fytd_diferencial_final = entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
            
            self.stdout.write(f"    diferencial_mtd sum: ${total_diferencial_mtd:,.2f}")
            self.stdout.write(f"    fytd_diferencial_final sum: ${total_fytd_diferencial_final:,.2f}")
            
            if is_first_fiscal_month:
                if abs(total_diferencial_mtd - total_fytd_diferencial_final) < 0.01:
                    self.stdout.write(self.style.SUCCESS("    ✓ Values match correctly"))
                else:
                    self.stdout.write(self.style.ERROR("    ✗ Values don't match - there may be an issue"))

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDRY RUN COMPLETE - Would have fixed {total_fixes} entries"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nValidation and fix complete! Fixed {total_fixes} entries total"))
