# ArgusWebApp

ArgusWebApp is a Django web app version of [argus_gui](https://github.com/kilmoretrout/argus_gui). It currently only implements the Wand module. 

## App Structure
- /accounts contains code for user accounts.
- /argus_app contains the Wand implementation.
- /argus_web_app is the Django wrapper for the whole app. Settings and routing are managed in here.

## Current Status
- Can run the wand with paired and unpaired points.
- Can visually view results once Wand has finished running.
- Can download result files individually and collectively as .zip.
- Can create user account and sign in/out.

## TODOs
- Enable Wand to be run with reference points.
- Add password reset.
- Enable account deletion.
- Allow logged in users to save their results to their account.
- Add a navigation bar to every page.
- Decide what the landing page should be and change the routing accordingly.

## Notes for Developers
- Django's `auth` library handles all the user account processes.
- Enabling reference points may simply be a matter of passing the ref point inputs from the form to the code. However, the Wand procedure was reworked when transferrring to web format and may have lost the capability to use reference points. If this is the case, that capability will need to be restored. Refer to [argus_gui](https://github.com/kilmoretrout/argus_gui) for code.
