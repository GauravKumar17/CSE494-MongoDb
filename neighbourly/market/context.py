from market.data import CATEGORIES
def site(request): return {'categories': CATEGORIES, 'account': getattr(request, 'account', None)}
