---
title: Release Version
nav_order: 2
parent: Version
description: Generate the changelog via git-cliff (prepending only the new version's section to CHANGELOG.md), commit and push it, create/move the supplied tags (deleting any pre-existing local or remote copies first), then create a GitHub Release whose body contains only the changelog entries for the new version.
layout: default
has_toc: false
---

<!-- markdownlint-disable MD022 MD025 -->
# Release Version
{: .no_toc }

Generate the changelog via git-cliff (prepending only the new version's section to CHANGELOG.md), commit and push it, create/move the supplied tags (deleting any pre-existing local or remote copies first), then create a GitHub Release whose body contains only the changelog entries for the new version.

{% include toc.md %}

---

{% include version-release.md %}
