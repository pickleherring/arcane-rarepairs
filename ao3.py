"""Scrape fic counts for Arcane pairs.

Searches for 1081 possible pairings, including characters with themselves.
To stay within AO3's rate limit for automated access, there is a 5-second pause between counts.
So this script will take quite a long time to run. You do the math.

Character list is read from 'characters.csv' with columns:
    name
    gender (f, m, other)

Results are saved to 'relationships.csv' with columns:
    A: character name
    B: character name
    type: relationship type (f/f, f/m, m/m, etc.)
    selfcest: is character with self? (True/False)
    count: number of fics found
"""

import itertools
import time

import bs4
import pandas
import regex
import requests


# NOTE: Set a very conservative sleep period to avoid AO3's rate limiting.
sleep_period = 5
backoff_factor = 60

url = 'https://archiveofourown.org/works/search'
search_field = 'work_search[query]'

work_count_pattern = regex.compile('[0-9]+')

champions = [
    'Caitlyn',
    'Ekko',
    'Heimerdinger',
    'Jayce',
    'Jinx',
    'Singed',
    'Vi',
    'Viktor',
]


class RateLimitedError(Exception):
    pass


def wrangle_fandom_tag(name):
    """Determine the appropriate fandom tag for an Arcane character.

    Follows AO3 wrangling guidelines for character tags:
    https://archiveofourown.org/wrangling_guidelines/7

    canonical character name is 'first name + last name' -> no fandom tag needed
    canonical character name is one name only -> fandom tag needed for disambiguation
    
    fandom for league champions is 'League of Legends'
    fandom for non-champion Arcane characters is 'Arcane: League of Legends'
    """

    if len(name.split()) > 1:
        return ''
    elif name in champions:
        return ' (League of Legends)'
    else:
        return ' (Arcane: League of Legends)'


def reverse_names(name):
    """Helper function for reversing name order.
    
    i.e. switches first name and last name
    """

    names = name.split()
    names.reverse()

    return ' '.join(names)


def wrangle_relationship_tag(name1, name2):
    """Determine the canonical relationship tag for a pairing.

    Follows AO3 wrangling guidelines for relationship tags:
    https://archiveofourown.org/wrangling_guidelines/8

    names in alphabetical order by last name, separated by slash
    at least one character does not need fandom disambiguation -> no overall fandom disambiguation
    both are single-name characters from same fandom -> overall fandom disambiguation at end
    both are single-name characters and only one is league champion -> separate disambiguation tags
    """

    name1, name2 = sorted((name1, name2), key=reverse_names)
    fandom1 = wrangle_fandom_tag(name1)
    fandom2 = wrangle_fandom_tag(name2)

    if (fandom1 == '') or (fandom2 == ''):
        fandom1 = ''
        fandom2 = ''
    elif fandom1 == fandom2:
        fandom1 = ''
    
    return f'{name1}{fandom1}/{name2}{fandom2}'


def get_work_count(session, name1, name2):
    """Get number of works for a relationship.

    Searches by canonical relationship tag (see wrangle_relationship_tag).
    Just reads the result count, doesn't check each work.
    This isn't perfect but is reasonably easy compared to laborious work-by-work checking. 
    """

    relationship_tag = wrangle_relationship_tag(name1, name2)

    response = session.get(url, params={search_field: f'"{relationship_tag}"'})

    if response.status_code == 429:
        raise RateLimitedError()

    soup = bs4.BeautifulSoup(response.text, features='lxml')
    main_div = soup.find('div', attrs={'id': 'main'})
    header = main_div.find('h3', attrs={'class': 'heading'})

    if header:
        work_count = int(work_count_pattern.match(header.get_text()).group(0))
    else:
        work_count = 0

    return work_count


if __name__ == '__main__':

    characters = pandas.read_csv('characters.csv')
    characters = characters.sort_values(['gender'])

    character_pairs = characters.itertuples(index=False, name=None)
    relationships = pandas.DataFrame(
        [itertools.chain(*x) for x in itertools.combinations_with_replacement(character_pairs, 2)],
        columns=['A', 'gender_A', 'B', 'gender_B']
    )

    relationships['type'] = relationships['gender_A'].str.cat(relationships['gender_B'], sep='/')
    relationships['selfcest'] = relationships['A'] == relationships['B']
    relationships = relationships[['A', 'B', 'type', 'selfcest']]

    n_pairs = relationships.shape[0]
    work_counts = []
    started = False

    session = requests.Session()
    session.mount(
        'https://',
        requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                status=7,
                status_forcelist=[429],
                backoff_factor=backoff_factor
            )
        )
    )

    for a, b in zip(relationships['A'], relationships['B']):

        if started:
            time.sleep(sleep_period)
        else:
            started = True

        work_count = get_work_count(session, a, b)
        work_counts.append(work_count)

        print(f'[{len(work_counts)} of {n_pairs}] {a}/{b}: {work_count}')
            
    relationships['count'] = work_counts
    relationships.to_csv('relationships.csv', index=False)
