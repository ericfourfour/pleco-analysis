# My Pleco Data Analysis

I have been studying Mandarin Chinese since January 2016. In April 2017, I started using Pleco to do flashcards. I find this to be a really great way to practice vocabulary.

Pleco stores all of the flashcard results in a SQLite database and I always thought about how I could do some kind of analysis on this.

## Getting the Data

One of the problems I encountered when I first looked into this is that Pleco only stores two dates for each flashcard: the first time your reviewed it, and the last time you reviewed it. All of the other times you reviewed it don't have a date (but at least they are kept in order).

To overcome this, every night I send a backup of my Pleco flashcard database to my Raspberry PI using FolderSync. This backup is stored in a dated folder so that I can have date-level accuracy on when I reviewed my flashcards.

I only started this nightly backup process in January 2019, so for anything before that, I use linear interpolation to fill in the missing dates.

## Preparing the Data

I took this opportunity to learn Pandas for doing data processing.

There are three dataframes I use to prepare the data for analysis:

### full_history

This dataframe contains a full history of each review event. I create this by processing each backup of the pleco database.

If I am not dealing with the first or last review of a flaschard, then I use linear interpolation to fill in the missing timestamps.

These are the main columns:

* review_ts - the exact (or estimated) timestamp of the review
* headword - the word on the flashcard
* result - whether I guessed the flaschard correctly

### prep

This dataframe is transformed from full history so that I am ready to analyse my performance on each headword / date.

These are the main columns:

* review_dt - the date of the review
* headword -  the word on the flashchard
* review_ts - the time-stamp of the review (used to specifically identify the review instance and for sorting)
* result - whether I guessed the flashcard correctly
* n_correct - the number of times I guessed this flashcard correctly up to this instance
* n_incorrect - the number of times I guess this flahcard incorrectly up to this instance
* last_result - whether I guessed this flaschard correctly at the end of day of this instance
* learned - whether this card could be considered learned as of this instance
* lag_learned - whether this card was considered learned as of the last instance
* net_learned - whether this card was learned, forgotten, or neither (1, -1, 0)

#### Learning

The way I calculate whether a card is learned is a function of n_correct, n_incorrect and last_result.

If the number of correct is greated than the number of incorrect and I guessed the card correctly by the end of the day, then I consider it learned. Otherwise, I do not consider it learned.

net_learned is used for aggregation in the analysis. If a word changes from not learned to learned, then that's +1. If a word changes from learned to not learned, then that's -1 (i.e. forgotten). If a word doesn't change (i.e. stays as learned or not leared), then that's 0.

### review

This dataframe is transformed from prep and is basically an aggregation down to the review_dt column. The columns are outlined in the analysis section below.

## Analysis

In my analysis, I looked at for each day (review_dt):

* How many cards I reviewed (n_reviewed)
* How many new words I was exposed to (new_vocab)
* How many were learned or forgotten (net_learned)
* The total words I was exposed to up to that date (vocab_size)
* The total words I learned or forgot up to that date (total_learned)

## Reports

### As of 2019-09-02

![screenshot](/images/20190902.png)

#### Insights

* The red box indicates when I went to China. There was a slight inspiration here to practice flashcards, although at the time I used a different app.

* The first purple line indicates when I joined my current company. I switched to commuting mainly on the subway which means I didn't have much internet access. So I assume I did more flashcards at the time.

* The blue line indicates when I started using SRS (spaced repetition). This is much more effective than random flashcards so my learning rate should improve here. Also I should be more inspired at the time.

* The green line indicates when I started taking daily backups of my Pleco database to improve accuracy. After this date, you can see which days I commuted to work in the n_reviewed line.

* The second purple line indicates when my team was restructured which allowed me to work from home more often. As I commuted less, I did flashcard less-and-less as well.
