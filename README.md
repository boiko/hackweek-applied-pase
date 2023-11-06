# hackweek-applied-pase
Patch search applied to openSUSE products


## Introduction

When issues are found in software (being them security or not), it is not always trivial to find and keep track of all products and versions that could potentially be affected by them. This is even more difficult when one is not familiar with the code base at hand and could lead to mistakes in the assessment. Some time ago, there was a project proposed (named PaSe) that aimed at using text search to find places where patches are or can be applied.


## Project Description

This hackweek project uses PaSe as a base for expanding on the scope to allow for a more automated code assessment. The ideas:

* Periodically index all sources from a given product
* Monitor an input stream of changes (patches added to packages of a given project, for example)
* Report other places where there is a match for the code (either applied or not applied)
* Validate if matching patches can really be applied

## Goals for this Hackweek

* Define and implement code to generate the pool of sources to be indexed
* If not yet done, containerize PaSe to make it easier to deploy
* Define and implement a feed of changes we want to scan (factory changes, bugzilla patches, etc…)
* Implement a service to consume the feed of changes and report results
* Implement a dashboard of results
* Expand the service to try to apply the patch (in dry mode or in a sandbox copy of the sources)


