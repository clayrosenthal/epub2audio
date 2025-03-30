---
description: 
globs: 
alwaysApply: false
---
# Project overview

The goal of this project is to take in ebooks and output audio books with as much of the same metadata as the original.

The audio files should use the file format's tools to indicate chapters in the audio book, based on the chapters within the book.

This project uses `mise` for its tools.

## Tools

- lint: `mise lint`
- format: `mise format`
- unit testing: `mise test`
- generate sample epub: `mise generate-sample-epub`
- read an epub using the parser: `mise read-epub {path_to_epub}`

You should run the tests after your changes, and revise them if the tests don't pass

