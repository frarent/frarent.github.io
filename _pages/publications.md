---
title: "Publications"
permalink: /publications/
description: "Selected publications, working papers and current work by Francesco Rentocchini."
---

<p class="note">For the full list of publications see
<a href="https://scholar.google.com/citations?user=2cH43vsAAAAJ&hl=en">Google Scholar</a>,
<a href="https://ideas.repec.org/e/pre185.html">IDEAS/RePEc</a> and
<a href="https://orcid.org/0000-0002-6414-0577">ORCID</a>.</p>

## Selected publications

<ul class="pubs">
{% for p in site.data.publications.selected %}
  <li>
    <span class="pub__title"><a href="https://doi.org/{{ p.doi }}">{{ p.title }}</a></span><br>
    <span class="pub__authors">{{ p.authors }} ({{ p.year }})</span><br>
    <span class="pub__venue"><em>{{ p.journal }}</em>{% if p.volume and p.volume != "" %}, {{ p.volume }}{% endif %}{% if p.pages and p.pages != "" %}, {{ p.pages }}{% endif %}</span>
  </li>
{% endfor %}
</ul>

{% comment %} Working papers: curated in _data/publications.yml. Current work: generated weekly from the
drafts in the project repositories (the local config -> _data/current_work.json). {% endcomment %}

## Working papers

<ul class="pubs">
{% for p in site.data.publications.working_papers %}
  <li>
    <span class="pub__title">{% if p.url and p.url != "" %}<a href="{{ p.url }}">{{ p.title }}</a>{% else %}{{ p.title }}{% endif %}</span><br>
    <span class="pub__authors">{{ p.authors }}</span>
    <span class="badge">{{ p.status }}</span>
  </li>
{% endfor %}
</ul>

## Current work

<ul class="pubs">
{% for p in site.data.current_work.papers %}
  <li>
    <span class="pub__title">{{ p.title }}</span><br>
    <span class="pub__authors">{{ p.authors }}</span>
  </li>
{% endfor %}
</ul>
