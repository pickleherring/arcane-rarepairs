from urllib import parse

import pandas
import plotnine
import streamlit

import ao3


n_rarepairs = 20
n_top_pairs = 5


streamlit.title('Arcane rarepairs')
streamlit.markdown('Browse fanfiction rarepairs from the acclaimed steampunk melodrama *Arcane*.')
streamlit.caption('last updated: 15th Oct 2022')
streamlit.markdown("""
---

**← select pairing types from among those on the left**

**← check 'selfcest' to also include pairings of characters with themselves**

**↓ browse the 'rarepairs' and 'zeropairs' tab for rare or nonexistent pairings**

---
""")


streamlit.sidebar.subheader('filters')

relationships = pandas.read_csv('relationships.csv')

selected_types = streamlit.sidebar.multiselect(
    'relationships',
    relationships['type'].unique(),
    default=relationships['type'].unique()
)

relationships = relationships[relationships['type'].isin(selected_types)]

if not streamlit.sidebar.checkbox('selfcest'):
    relationships = relationships[~relationships['selfcest']]


if selected_types:

    streamlit.subheader('results')

    top_tab, rare_tab, zero_tab = streamlit.tabs(['top pairs', 'rarepairs', 'zeropairs'])

    with top_tab:

        top_pairs = relationships.nlargest(n_top_pairs, ['count'])
        top_pairs = top_pairs.sort_values(['count'])
        top_pairs['pair'] = top_pairs['A'].str.cat(top_pairs['B'], sep='/')

        top_pairs['pair'] = pandas.Categorical(
            top_pairs['pair'],
            categories=top_pairs['pair'].tolist()
        )

        fig = (
            plotnine.ggplot(top_pairs)
            + plotnine.aes(
                x='pair',
                y='count',
                label='count'
            )
            + plotnine.geom_col()
            + plotnine.geom_text()
            + plotnine.coord_flip()
        )

        streamlit.pyplot(fig.draw())

    with rare_tab:

        rarepairs = relationships[relationships['count']>0].nsmallest(n_rarepairs, ['count'], keep='all')

        for row in rarepairs.itertuples(index=False):

            query = parse.quote_plus(ao3.wrangle_relationship_tag(row.A, row.B))
            url = f'{ao3.url}?{ao3.search_field}="{query}"'

            streamlit.markdown(f'* [{row.A}/{row.B}]({url}) ({row.count})')

    with zero_tab:
        
        zeropairs = relationships[relationships['count']==0]
        
        for row in zeropairs.itertuples(index=False):
            streamlit.markdown(f'* {row.A}/{row.B}')


streamlit.markdown("""
---

Fic counts taken from a web scrape of [archiveofourown.org](https://archiveofourown.org).

Counts represent the number of search results when searching for the [canonical relationship tag](https://archiveofourown.org/wrangling_guidelines/8) for the pair.
This is not always an accurate reflection of the true total, as authors may use alternative tags, especially for rarepairs.
This is the best I could do without a massive pile of work and I am lazy.

See the source code for this app and for the AO3 scraping program [here](https://github.com/pickleherring/arcane-rarepairs).
""")
