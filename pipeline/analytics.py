"""
Shared GA4 snippet for the standalone pages the pipeline generates.

The area apps and the hub carry the tag inline in their own templates, but the
event pages, guides and this-weekend pages did not — which meant analytics was
blind on exactly the pages organic search lands on. One definition here so the
measurement ID lives in a single place.
"""

GA_MEASUREMENT_ID = 'G-FXMDYPK8KZ'

GA_SNIPPET = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', '{GA_MEASUREMENT_ID}', {{ 'anonymize_ip': true }});
</script>"""
