"""School-specific parsers for economics PhD placement data."""
from .base import SchoolParser

# Original 10 parsers
from .princeton import PrincetonParser
from .uchicago import UChicagoParser
from .nyu import NYUParser
from .stanford import StanfordParser
from .mit import MITParser
from .yale import YaleParser
from .brown import BrownParser
from .penn import PennParser
from .maryland import MarylandParser
from .cmu import CMUParser

# New 14 parsers
from .harvard import HarvardParser
from .berkeley import BerkeleyParser
from .northwestern import NorthwesternParser
from .columbia import ColumbiaParser
from .michigan import MichiganParser
from .ucla import UCLAParser
from .wisconsin import WisconsinParser
from .duke import DukeParser
from .minnesota import MinnesotaParser
from .cornell import CornellParser
from .washington import WashingtonParser
from .illinois import IllinoisParser
from .virginia import VirginiaParser
from .utaustin import UTAustinParser

# Map school names to their custom parsers
CUSTOM_PARSERS = {
    # Original 10
    'Princeton': PrincetonParser(),
    'University of Chicago': UChicagoParser(),
    'NYU': NYUParser(),
    'Stanford': StanfordParser(),
    'MIT': MITParser(),
    'Yale': YaleParser(),
    'Brown': BrownParser(),
    'University of Pennsylvania': PennParser(),
    'University of Maryland': MarylandParser(),
    'Carnegie Mellon': CMUParser(),
    # New 14
    'Harvard': HarvardParser(),
    'UC Berkeley': BerkeleyParser(),
    'Northwestern': NorthwesternParser(),
    'Columbia': ColumbiaParser(),
    'University of Michigan': MichiganParser(),
    'UCLA': UCLAParser(),
    'University of Wisconsin': WisconsinParser(),
    'Duke': DukeParser(),
    'University of Minnesota': MinnesotaParser(),
    'Cornell': CornellParser(),
    'University of Washington': WashingtonParser(),
    'University of Illinois': IllinoisParser(),
    'University of Virginia': VirginiaParser(),
    'UT Austin': UTAustinParser(),
}

__all__ = [
    'SchoolParser', 'CUSTOM_PARSERS',
    # Original
    'PrincetonParser', 'UChicagoParser', 'NYUParser',
    'StanfordParser', 'MITParser', 'YaleParser',
    'BrownParser', 'PennParser', 'MarylandParser', 'CMUParser',
    # New
    'HarvardParser', 'BerkeleyParser', 'NorthwesternParser',
    'ColumbiaParser', 'MichiganParser', 'UCLAParser',
    'WisconsinParser', 'DukeParser', 'MinnesotaParser',
    'CornellParser', 'WashingtonParser', 'IllinoisParser',
    'VirginiaParser', 'UTAustinParser',
]
