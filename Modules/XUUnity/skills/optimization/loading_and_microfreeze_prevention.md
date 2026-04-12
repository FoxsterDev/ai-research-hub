# Skill: Loading And Microfreeze Prevention

## Use For
- scene transitions
- async loading
- popup opening
- reward flows
- startup-sensitive work

## Rules
- Break long work into controlled steps when it must happen on the main thread.
- Do not hide blocking work behind async wrappers that still stall the frame.
- Preload or warm critical content before user-visible transitions where possible.
- Watch for UI rebuild spikes, asset deserialization bursts, and callback storms.
- Treat even short hitches on reward, fail, resume, and purchase flows as high severity.
- Keep blocking work off the Android main thread and off iOS lifecycle-sensitive UI paths.
- Prefer managed-side caching of immutable native results instead of repeated bridge crossings on hot flows.
- For UI-heavy mobile projects, review async upload settings and atlas loading behavior if large textures or atlases can fall back to synchronous upload.
- Treat WebView, ad overlay, and context-restore transitions as high-risk hitch points on Android.
- Audit non-interactive UI graphics and masks when touch latency or draw-call spikes appear on dense screens.
