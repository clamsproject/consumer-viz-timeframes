from viz_timeframes import render_text
from viz_timeframes.extract import Segment, Track

MINUTE = 60000


def track(*frames):
    return Track('v_0', 'app', [Segment(*f) for f in frames])


def chars_of(t):
    return render_text.assign_chars(render_text.label_totals(t))


def test_language_codes_get_their_first_letters():
    chars = render_text.assign_chars({'es': 50, 'en': 40, 'fr': 10})
    assert chars == {'en': 'E', 'es': 'S', 'fr': 'F'}


def test_same_labels_get_same_letters_in_any_order_of_time():
    assert (render_text.assign_chars({'chyron': 1, 'credits': 2})
            == render_text.assign_chars({'chyron': 2, 'credits': 1}))


def test_labels_beyond_the_limit_share_one_character():
    totals = {f'speaker_{i:02d}': 100 - i for i in range(30)}
    chars = render_text.assign_chars(totals)
    named = [c for c in chars.values() if c != render_text.OTHER_CHAR]
    assert len(named) == len(set(named)) == render_text.MAX_NAMED
    assert all(c.isupper() for c in named)
    # the labels with the least time share the character
    assert chars['speaker_29'] == render_text.OTHER_CHAR
    assert chars['speaker_00'] != render_text.OTHER_CHAR


def test_case_shows_how_much_of_a_character_the_label_covers():
    t = track((0, 10000, 'en'), (10000, 20000, 'es'), (20000, 21000, 'en'))
    assert render_text.render_chars(t, chars_of(t), 40000) == 'ESe.'


def test_short_last_character_is_judged_by_its_own_length():
    t = track((0, 12000, 'en'), (13000, 15000, 'es'))
    # the last 5 s hold 2 s of each label
    assert render_text.render_chars(t, chars_of(t), 15000) == 'Ee'
    t = track((0, 13000, 'en'))
    assert render_text.render_chars(t, chars_of(t), 15000) == 'EE'


def test_vote_uses_the_shared_character():
    # three small labels together cover more than the big one
    t = track((0, 4000, 'a'), (4000, 6000, 'b'), (6000, 8000, 'c'),
              (8000, 10000, 'd'))
    chars = {'a': 'A', 'b': '*', 'c': '*', 'd': '*'}
    assert render_text.render_chars(t, chars, 10000) == '*'


def grouped(n_minutes, rest=''):
    return ' '.join(['E' * 6] * n_minutes + ([rest] if rest else []))


def test_rows_are_ten_minutes_in_groups_of_one_minute():
    rows = render_text.render_rows('E' * 152, 25 * MINUTE + 20000)
    assert rows == [' 0:00 |' + grouped(10) + '|',
                    '10:00 |' + grouped(10) + '|',
                    '20:00 |' + grouped(5, 'EE') + '|']


def test_rows_show_hours_for_long_timelines():
    duration = 2 * 3600000
    rows = render_text.render_rows('E' * (duration // 10000), duration)
    assert rows[0].startswith('0:00:00 |')
    assert rows[-1].startswith('1:50:00 |')


def test_legend_counts_overlapping_time_once():
    t = track((0, 6000, 'a'), (4000, 10000, 'b'))
    legend = render_text.render_legend(t, chars_of(t), 20000, 80)
    assert '.: no TimeFrame (50%)' in legend


def test_legend_shows_small_shares_and_counts():
    t = track((0, 999, 'en'), (999, 1000, 'fr'), (1000, 1999, 'en'))
    legend = render_text.render_legend(t, chars_of(t), 2000, 80)
    assert 'E: en (100%, 2 TimeFrames)' in legend
    assert 'F: fr (<1%, 1 TimeFrame)' in legend


def test_output_fits_the_rows():
    t = track(*((i * MINUTE, (i + 1) * MINUTE, f'label_{i}')
                for i in range(20)))
    out = render_text.render([t], 20 * MINUTE)
    assert '*: 10 other labels' in out
    width = len(' 0:00 |' + grouped(10) + '|')
    assert all(len(line) <= width for line in out.splitlines())


def test_hour_rows_fit_80_columns():
    duration = 2 * 3600000
    rows = render_text.render_rows('E' * (duration // 10000), duration)
    assert all(len(row) <= 80 for row in rows)
