# XUUnity Vendor Note: Facebook (Meta) Unity SDK — runtime cost

## Use For
Startup or scene-load spikes on Android in apps that ship the Facebook Unity SDK (`facebook-sdk-for-unity`), and review of FB SDK upgrades for runtime cost. For Meta Audience Network as an ad network see `knowledge/vendors/applovin/mediators/facebook_meta.md`.

## Codeless IAP scan (verified in SDK source, tags 17.0.2, 18.1.1, 19.0.0)
- `AndroidFacebookGameObject` calls `CodelessIAPAutoLog.addListenerToIAPButtons` in `OnAwake` and again from its `SceneManager.sceneLoaded` handler (`OnSceneLoaded`).
- The call walks every type in every loaded assembly looking for Unity IAP buttons. It is unconditional:
  - the `AutoLogAppEventsEnabled` manifest/settings flag does not gate it;
  - the Meta dashboard "Log In-App Purchases Automatically" toggle does not gate it.
- Measured on a low-end Android device without Unity IAP: about 200 ms and about 0.9 MB of garbage per scene load, plus about 435 ms at SDK init.

## Mitigation (apps without Unity IAP buttons)
- After `FB.Init` completes, unsubscribe the SDK object's private `OnSceneLoaded` handler from `SceneManager.sceneLoaded`:
  - resolve the type and method by name once;
  - find the SDK game object instance;
  - remove a delegate built for that instance.
- If the type, method or instance is not found (a renamed SDK internal), log a warning and leave the SDK untouched. Do not throw.
- Android player only. Re-verify on every SDK upgrade: the handler is private API.
- The `OnAwake` scan cannot be removed this way; it needs a patched SDK build.
- Do not apply this when the app uses Unity IAP codeless buttons. That listener is what logs those purchases.

## Upgrade Check
When updating the SDK, search its source for `CodelessIAPAutoLog` and `sceneLoaded` to confirm whether the scan and the handler name still exist.
