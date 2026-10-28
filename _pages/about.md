---
permalink: /
title: "Francesco Rentocchini"
hide_title: true
description: "Economist at the University of Ferrara working on the economics of innovation and science, industrial organisation, innovation policy and entrepreneurship."
redirect_from:
  - /about/
  - /about.html
---

# About

Francesco Rentocchini is an economist at the **University of Ferrara** (Italy), where he teaches in and
sits on the faculty board of the PhD programme in
[*Economics, Management and Methods for the Sustainable Transition* (ECMAN)](https://iuss.unife.it/en/phd/phd-programs/courses/ecman).

From 2020 to 2026 he was **Senior Economic Analyst** at the European Commission's
[Joint Research Centre (JRC)](https://iri.jrc.ec.europa.eu/home/) in Seville, where he worked on industrial
R&D, mergers and acquisitions and intellectual property, including the *EU Industrial R&D Investment Scoreboard*.
From 2016 to 2026 he was **Associate Professor of Business Economics** at the
[Department of Economics, Management and Quantitative Methods (DEMM)](https://demm.unimi.it/en) of the University of Milan. Before that,
he was Lecturer and then Associate Professor in Strategy and Innovation at the
[University of Southampton](https://www.southampton.ac.uk/) (UK).

His research is in the **economics of innovation and science**, **industrial organisation**, **innovation
policy** and **entrepreneurship**. He studies the two-way flows between the production of scientific knowledge and
the development of technological innovation, the green and digital transitions, start-ups and firm growth, and
university–industry collaboration. His articles have appeared in, among others, *Research Policy*, *Industrial
and Corporate Change*, the *International Journal of Industrial Organization*, *Oxford Economic Papers*,
*Regional Studies* and *Small Business Economics*.

He was Associate Editor of the *European Management Review* (2016–2020) and guest editor for *Industry and
Innovation* and *Small Business Economics*. From 2020 to 2025 he was a member of the external faculty board of the
[PhD programme in Regional Science and Economic Geography](https://www.gssi.it/education/regional-science-economic-geography)
at the Gran Sasso Science Institute (GSSI). He has held research periods at the Manchester Institute of Innovation
Research (UK), UNU-MERIT (the Netherlands) and INGENIO (Spain), and holds a PhD from the University of Bologna.

## Current positions

<ul class="positions">
{% for p in site.data.positions.current %}
  <li><span class="dates">{{ p.dates }}</span>
      <span><span class="role">{{ p.role }}</span>
      <span class="org">{% if p.url %}<a href="{{ p.url }}">{{ p.org }}</a>{% else %}{{ p.org }}{% endif %}, {{ p.place }}</span></span></li>
{% endfor %}
</ul>

## Previous positions

<ul class="positions">
{% for p in site.data.positions.previous %}
  <li><span class="dates">{{ p.dates }}</span>
      <span><span class="role">{{ p.role }}</span>
      <span class="org">{% if p.url %}<a href="{{ p.url }}">{{ p.org }}</a>{% else %}{{ p.org }}{% endif %}, {{ p.place }}</span></span></li>
{% endfor %}
</ul>

## Education

<ul class="positions">
{% for p in site.data.positions.education %}
  <li><span class="dates">{{ p.dates }}</span>
      <span><span class="role">{{ p.role }}</span>
      <span class="org">{{ p.org }}, {{ p.place }}</span></span></li>
{% endfor %}
</ul>
