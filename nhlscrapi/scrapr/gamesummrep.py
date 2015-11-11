from nhlscrapi._tools import to_int
from nhlscrapi._tools import split_time
from nhlscrapi._tools import exclude_from as ex_junk
from nhlscrapi.games.playbyplay import Strength
from nhlscrapi.scrapr.reportloader import ReportLoader
from nhlscrapi.scrapr.teamnameparser import team_abbr_parser

class GameSummRep(ReportLoader):
    """Retrieve and load game summary report from nhl.com"""

    def __init__(self, game_key):
        super(GameSummRep, self).__init__(game_key, 'game_summary')

        self.goalie_summary = {'away': {}, 'home': {}}
        """
        Property that returns the home/away team goalies.
        :returns: dict of the form
        .. code:: python
            {
                'home/away': {
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
            }
        """

    def parse(self):
        # Brian TBD: does not match other parse methods, success should return self, None otherwise.
        """Fully parses game summary report.
        :returns: boolean success indicator
        :rtype: bool """

        r = super(GameSummRep, self).parse()
        try:
            self.parse_scoring_summary()
            self.parse_goaltender_summary()
            return r and False
        except:
            return False

    def parse_scoring_summary(self):
        lx_doc = self.html_doc()

        main = lx_doc.xpath('//*[@id="MainTable"]')[0]
        scr_summ = main.xpath('child::tr[4]//tr')
        for r in scr_summ:
            #print r.get('class')
            if r.get('class') in ['oddColor', 'evenColor']:
                tds = r.xpath('./td')
                scr = [td.xpath('text()') for td in tds[:8]] #Track for later - can add [0] index inside to avoid using it below

                # goal summry data
                goals = {}

                # goal num, game state, scoring team
                gn = to_int(scr[0][0]) if scr[0] else -1
                period = self.__period(scr[1])
                time = split_time(scr[2][0] if period < 4 else '0:00')
                strength = self.__strength(scr[3][0] if scr[3] else 'EV')
                team = team_abbr_parser(scr[4][0])

                # skaters on the ice
                sks = tds[8:]
                goals[gn] = {
                    'per': period,
                    'time': time,
                    'strength': strength,
                    'team': team,
                    'home': self.__skaters(sks[0]),
                    'away': self.__skaters(sks[1])
                }

                scorer = self.__scorer(scr[5][0])

                # Brian: Fixing issue with syntax, need to revisit the following block of code
                #        to ensure that the logic is correct
                assists = []
                if scorer['num'] in goals[gn]:
                    for s in scr[6:8]:
                        if s and s[0] != u'\xa0':
                            assists.append(self.__scorer(s[0]))
                # EndBrian

                #print {
                #    'goal_num': gn,
                #    'scorer': scorer,
                #    'assists': assists
                #}

    def parse_goaltender_summary(self):
        lx_doc = self.html_doc()

        main = lx_doc.xpath('//*[@id="MainTable"]')[0]
        goal_summ_table = main.xpath('child::tr[15]//tr')

        team = 'away'
        for row in goal_summ_table:
            cells = [td.xpath('text()')[0] for td in row.xpath('./td')]
            if len(cells) == 1: #There's a divider row with 1 cell that separates the teams. Away is always first.
                team = 'home' #Home from here on out

            if row.get('class') in ['oddColor', 'evenColor']:
                g = {}
                g['pos'] = 'G'

                #Parse name + win/loss status
                name_break = cells[2].replace(',','').split(' ')  # 'LAST, FIRST (W)' -> ['GRUBAUER', 'PHILIPP', '(W)']
                g['name'] = {'first': name_break[1], 'last': name_break[0]}
                if len(name_break) == 2:
                    g['result'] = ''  # Neither win nor loss.
                else:
                    g['result'] = name_break[2][1:-1]  # '(W)' -> 'W' // '(OT)' -> 'OT'

                # Build the TOI info
                g['toi'] = {}
                for key, val in (('ev', cells[3]), ('pp', cells[4]), ('sh', cells[5]), ('tot', cells[6])):
                    min, sec = val.split(':') if val != u'\xa0' else ('', '')
                    g['toi'][key] = {'min': min, 'sec': sec}

                # Tally goals and shots against
                # QUESTION FOR LATER: What's the appropriate naming convention for the periods (1st, 2nd, 3rd)?
                # Revise this data structure later.
                g['ga'] = {}
                g['sa'] = {}

                kvps = (('per1', cells[7]), ('per2', cells[8]), ('per3', cells[9]), ('tot', cells[10]))
                if len(cells) == 12:
                    kvps = (('per1', cells[7]), ('per2', cells[8]), ('per3', cells[9]), ('ot', cells[10]), ('tot', cells[11]))

                # This setup causes an interesting issue, if a goalie faces no shots in OT, stats are reported as if
                # they never played. See Mrazek in game #194 of 2015-16 season. Do we fill in OT as zero?
                for key, val in kvps:
                    if val != u'\xa0':  # Just leave empty if we got an empty cell.
                        goals, shots = val.split('-')
                        g['ga'][key] = int(goals)
                        g['sa'][key] = int(shots)

                self.goalie_summary[team][int(cells[0])] = g

    def __period(self, scr):
        period = 0
        if scr:
            if scr[0] == 'SO':
                period = 5
            elif scr[0] == 'OT':
                period = 4
            else:
                period = to_int(scr[0])

        return period

    def __strength(self, sg_str):
        if 'PP' in sg_str:
            return Strength.PP
        elif 'SH' in sg_str:
            return Strength.PP
        else:
            return Strength.Even

    def __position(self, long_name):
        return ''.join(s[0] for s in long_name.split(' '))

    def __scorer(self, num_name_tot):
        nnt = num_name_tot.replace('(', ' ').replace(')', '')
        nnt_l = nnt.split(' ')
        return {
            'num': to_int(nnt_l[0]),
            'name': nnt_l[1].split('.')[1].strip(),
            'seas_tot': to_int(nnt_l[2]) if len(nnt_l) == 3 else -1
        }

    def __skaters(self, td):
        sk_d = {}
        for sk in td.xpath('./font'):
            pos_pl = sk.get('title').split(' - ')
            num = to_int(sk.xpath('text()')[0])
            if num > 0:
                sk_d[num] = {
                    'pos': self.__position(pos_pl[0]),
                    'name': pos_pl[1]
                }

        return sk_d