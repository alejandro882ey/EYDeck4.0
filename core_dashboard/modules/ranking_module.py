from django.db.models import Sum


def compute_ranking(queryset, group_by_field, revenue_field='fytd_ansr_sintetico'):
    """Return full ranking and top 5 for a queryset grouped by group_by_field.

    Args:
        queryset: Django QuerySet of RevenueEntry-like objects
        group_by_field: string name of the field to group by (e.g., 'engagement_manager')
        revenue_field: field name to sum as revenue

    Returns:
        (top5_list, full_ranking_list) where each list contains dicts with keys:
           - 'label' (group value)
           - 'total_revenue'
    """
    grouped = queryset.values(group_by_field).annotate(total_revenue=Sum(revenue_field)).order_by('-total_revenue')

    full = [
        {
            'label': item[group_by_field],
            'total_revenue': item['total_revenue'] or 0
        }
        for item in grouped
    ]

    top5 = full[:5]
    return top5, full
