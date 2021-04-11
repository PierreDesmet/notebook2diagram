try:
    from faker import Faker
except:
    raise ImportError('faker must be pip installed first: https://pypi.org/project/Faker/')

fake = Faker(['fr_FR'])

def generate(what: str, n: int = 1):
    """
    what: any of address | ascii_safe_email | siren | postcode | and so on...
    """
    return [getattr(fake, what)() for _ in range(n)]
