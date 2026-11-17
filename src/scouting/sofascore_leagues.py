"""Verified competition/season scopes. Provider IDs are never inferred from a league name."""
from dataclasses import dataclass


@dataclass(frozen=True)
class League:
    key: str
    country: str
    division: str
    competition: str
    season: str
    tournament_id: int
    season_id: int
    folder: str
    schedule_hour: int
    allow_name_match: bool = False

    @property
    def scope(self):
        return dict(country=self.country, division=self.division, competition=self.competition, season=self.season)


DEFAULT_LEAGUE = League('cl_primera', 'cl', 'primera', 'Primera División Chile', '2026',
                        11653, 88493, 'data/recovery/manual-2026', 6, allow_name_match=True)
LEAGUES = {league.key: league for league in (
    DEFAULT_LEAGUE,
    League('cl_primera_b', 'cl', 'primera_b', 'Primera B Chile', '2026',
           1240, 89007, 'data/recovery/cl-primera-b-2026', 7),
)}
