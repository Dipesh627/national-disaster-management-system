"""
NDMS legal-document settings (Terms & Conditions + Privacy Policy).

This is the ONE place to edit when the legal text is revised.

When you make a meaningful change to terms.html or privacy.html:

  1. Update LEGAL_LAST_UPDATED (shown on both pages).
  2. Bump TERMS_VERSION (for example "1.0" -> "1.1").

TERMS_VERSION covers both documents together. It is saved on each
new account at registration (User.terms_version), so you can always
tell which version of the text a person accepted.

The "Last Updated" date is a plain string on purpose: it changes only
when YOU edit it, never automatically.
"""

# Version of the Terms & Conditions and Privacy Policy accepted at
# registration. Stored on the user record.
TERMS_VERSION = '1.0'

# Human-readable revision date shown at the top of both legal pages.
LEGAL_LAST_UPDATED = 'September 2026'

# Contact address shown in the legal pages. Same address that is
# already published in the Contact section of the home page.
LEGAL_CONTACT_EMAIL = 'info@ndms.com.np'