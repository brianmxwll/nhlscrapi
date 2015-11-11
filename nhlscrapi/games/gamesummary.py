# annoying boilerplate
# get access to other sub folders
import sys
sys.path.append('..')

from nhlscrapi.scrapr.gamesummrep import GameSummRep
from nhlscrapi.games.repscrwrap import RepScrWrap


class GameSummary(RepScrWrap):
    def __init__(self, game_key):
        super(GameSummary, self).__init__(game_key, GameSummRep(game_key))

        self._summary_rep = GameSummRep(game_key)

        # Just tell it to parse for now, activate relevant code.
        self._summary_rep.parse()

        #  @RepScrWrap.read_banner('_roster_rep')
        #  @RepScrWrap.lazy_load('_roster_rep', 'parse_rosters')

    @property
    def away_goalies(self):
        """
        Property that returns the away team goalies ..
        :returns: dict of the form
        .. code:: python
            {
                num: {
                    'ga': { 'per1/per2/per3/ot/tot': value },
                    'name': { 'first': first, 'last': last },
                    'pos': 'G'
                    'result': value,
                    'toi': {
                        'tot/pp/sh/ev': { 'min': mins, 'sec': secs }
                    }
                }
            }
        """
        return self._summary_rep.goalie_summary['away']

    @property
    def home_goalies(self):
        """
        Property that returns the home team goalies ..
        :returns: dict of the form
        .. code:: python
            {
                num: {
                    'ga': { 'per1/per2/per3/ot/tot': value },
                    'name': { 'first': first, 'last': last },
                    'pos': 'G'
                    'result': value,
                    'toi': {
                        'tot/pp/sh/ev': { 'min': mins, 'sec': secs }
                    }
                }
            }
        """
        return self._summary_rep.goalie_summary['home']