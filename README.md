# Slackdump search

A python script to help search archives made by the very excellent [slackdump](https://github.com/rusq/slackdump).

This script is built specifically to work with an archive from slackdump in the "mattermost" format with "chunked" JSON messages.
These are the defaults using the archive option with slackdump.
They have good documentation on both of these format details, in particular how the chunked JSON represenations work.

For transparency, here's how I generated an archive

```
go run ./cmd/slackdump archive -enterprise [list of channels]
```

This was all tested with an ~11GB, ~800 channel archive (most of the bulk seems to be file attachments).

## Usage

First, run the web server from slackdump:

```sh
go run ./cmd/slackdump view slackdump_20240807_214838
```

Next, we have a few options to run this tool.
The easiest is just to run the Python script directly.
The links assume that the viewer from slackdump is running on localhost:8080.
Run slack search:

```
python3 slack_search.py slackdump_20240807_214838 slackdump_20240807_214838 'email_name ILIKE'
```

I was looking for sql queries that I'd written (or been messaged)
that had a filter on `email_name`.
This works!
It returned 4 results for my archive.

I also tried more common search terms,
with up to 200 results working fine
(I didn't test anything broader).
