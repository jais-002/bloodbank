"""
NoCacheForAuthUsers middleware
──────────────────────────────
Problem: When a logged-in user clicks "Logout" and then presses the
         browser Back button, the browser displays the cached version of
         protected pages — no server request is made, so @login_required
         never gets a chance to redirect them.

Fix:     Attach Cache-Control: no-store, no-cache, must-revalidate headers
         to every HTTP response served to a logged-in user.  This tells all
         browsers (and any intermediate proxy) to NEVER store those pages.
         On Back, the browser is forced to contact the server; the server
         detects the session is gone and redirects to /login/.
"""


class NoCacheForAuthUsersMiddleware:
    """Prevent authenticated pages from being stored in the browser cache."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only patch responses for logged-in users (anonymous visitors can
        # still benefit from normal browser caching for public pages).
        if hasattr(request, 'user') and request.user.is_authenticated:
            # The gold-standard set of headers understood by every browser:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'   # HTTP/1.0 back-compat
            response['Expires'] = '0'         # Proxies/IE back-compat

        return response
