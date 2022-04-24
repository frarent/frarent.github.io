---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

{% if 2cH43vsAAAAJ %}
  You can also find my articles on <u><a href="{{2cH43vsAAAAJ}}">my Google Scholar profile</a>.</u>
{% endif %}

{% include base_path %}

{% for post in site.publications reversed %}
  {% include archive-single.html %}
{% endfor %}
