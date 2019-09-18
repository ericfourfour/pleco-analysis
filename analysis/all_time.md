# All Time Analysis

I have been studying Mandarin Chinese since January 2017. In April 2017, I started using Pleco to do flashcards. I find this to be a really great way to practice vocabulary.

Pleco stores all of the flashcard results in a SQLite database and I always thought about how I could do some kind of analysis on this.

## Getting the Data

One of the problems I encountered when I first looked into this is that Pleco only stores two dates for each flashcard: the first time your reviewed it, and the last time you reviewed it. All of the other times you reviewed it don't have a date (but at least they are kept in order).

To overcome this, every night I send a backup of my Pleco flashcard database to my Raspberry PI using FolderSync. This backup is stored in a dated folder so that I can have date-level accuracy on when I reviewed my flashcards.

I only started this nightly backup process in January 2019, so for anything before that, I use linear interpolation to fill in the missing dates.

## Preparing the Data

I took this opportunity to learn Pandas for doing data processing.

There are three dataframes I use to prepare the data for analysis:

### card_events

This dataframe contains a full history of each flashcard review event. I create this by processing each backup of the pleco database.

If I am not dealing with the first or last review of a flaschard, then I use linear interpolation to fill in the missing timestamps.

Index:

* dictid / dictentry / hw / created - identifies a unique flashcard, the main component being the headword (hw)
* occurrence - the occurrence of that flashcard (starting at 0)

Columns:

* reviewedtime - the exact or estimated timestamp of the review
* result - whether I guessed the flaschard correctly

### hw_events

This dataframe simplifies the flashcard events to simply headword events. There are often multiple flashcards with the same headword and the headword is the main part of the flashcard you are tested on.

Index:

* hw - the headword
* occurrence - the occurrence of that headword

Columns:

* reviewedtime - the exact or estimated timestamp of the review
* result - whether I guessed the flaschard correctly

### hw_events_stats

This dataframe builds on the headword events and includes stats for each row to help with analysis.

Index:

* hw - the headword
* occurrence - the occurrence of that headword

Columns:

* reviewedtime - the exact or estimated timestamp of the review
* result - whether I guessed the flaschard correctly
* revieweddate - the date of the review
* cumcorrect - the cumulative number of times this flashcard was guessed correctly up to this occurrence
* cumincorrect - the cumulative number of times this flashcard was guessed incorrectly up to this occurrence
* daycorrect - number of times this flashcard was guessed correctly on this day
* dayincorrect - number of times this flashcard was guessed incorrectly on this day
* learned - whether this flashcard is considered "learned". A flashcard is considered "learned" if it was guessed correctly at least once and never guessed incorrectly on this day.
* laglearned - whether the previous occurrence of this flashcard was considered "learned"
* netlearned - whether this flashcard occurrence changed from unlearned to learned (1), learned to unlearned (-1), or was unchanged (0) (i.e. learned / forgotten / neither)

#### Learning

I have simplified the way I determine whether a card is considered learned. If I guess the card correct on my first try that day and I don't guess it incorrect any more times that day, then I consider it learned. If I ever guess a card incorrect, then I consider it not learned.

* When a flashcard changes from unlearned to learned, I call this "learned" and assign netlearned a value of 1
* When a flashcard changes from learned to unlearned, I call this "forgotten" and assign netlearned a value of -1
* When a flashcard doesn't change, I assign netlearned a value of 0.

By summing up the netlearned column, I can effectively determine how many cards I'm learning or forgetting.

## Analysis

In my analysis, I looked at for each day (review_dt):

* How many cards I reviewed (reviewed)
* How many new words I was exposed to (new)
* How many were learned or forgotten (netlearned)
* The cumulative new words I was exposed to up to that date (cumnew)
* The cumulative words I learned or forgot up to that date (cumnetlearned)

## Reports

### As of 2019-09-17

![screenshot](/images/all_time_20190917.png)

#### Insights

* The red box indicates when I went to China. There was a slight inspiration here to practice flashcards, although at the time I used a different app.

* The first purple line indicates when I joined my current company. I switched to commuting mainly on the subway which means I didn't have much internet access. So I assume I did more flashcards at the time.

* The blue line indicates when I started using SRS (spaced repetition). This is much more effective than random flashcards so my learning rate should improve here. Also I should be more inspired at the time.

* The green line indicates when I started taking daily backups of my Pleco database to improve accuracy. After this date, you can see which days I commuted to work in the n_reviewed line.

* The second purple line indicates when my team was restructured which allowed me to work from home more often. As I commuted less, I did flashcard less-and-less as well.
