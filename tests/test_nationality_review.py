import pandas as pd
import pytest

from scouting.services.nationality_service import nationality_group


@pytest.mark.parametrize('value', [pd.NA, 'Sin nacionalidad', 'SIN DATOS', 'No disponible'])
def test_missing_nationality_is_not_foreign(value):
    assert nationality_group(value) is None
