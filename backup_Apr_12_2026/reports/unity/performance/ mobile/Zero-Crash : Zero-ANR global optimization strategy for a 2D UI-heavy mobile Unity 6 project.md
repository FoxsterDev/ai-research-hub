# Engineering Review Artifact

## 1. Problem and Context
- **Problem:** Developing a "Zero-Crash / Zero-ANR" global optimization strategy for a 2D UI-heavy mobile Unity 6 project.
- **Goal:** Achieve maximum performance (flat shading, eliminated invisible GPU/CPU workloads, reduced thermal throttling) without compromising Figma-to-Unity color accuracy, UI texture crispness, or third-party SDK stability.
- **Context:** Mobile targets (iOS/Android). The application heavily relies on Canvas UI and integrates major Ad SDKs (AdMob, AppLovin, IronSource) which often utilize system WebViews and overlay rendering that must not be disrupted by engine-level graphics stripping.

## 2. Constraints
- **Runtime / platform constraints:**
  - Android ecosystem is highly fragmented; low-end and older devices (e.g., Samsung A-series 2018-2020) have unstable graphics drivers.
  - Ad SDKs often run in separate threads or rely on system `WebView` for HTML5 playable ads.
- **Performance constraints:**
  - Sustained performance is critical. Thermal throttling directly causes FPS drops and lowers Ad viewability/CPM.
  - Strict memory limits (RAM) to avoid Android Low Memory Killer (LMK) terminating the app during heavy video ad playback.
- **Correctness constraints:**
  - UI colors must match Figma hex codes exactly (Linear/Gamma safe).
  - UI sprites and TextMeshPro elements must remain perfectly crisp (no aggressive compression artifacts).
- **API / usability constraints:**
  - Editor-time optimizations must be modular, allowing for A/B testing of specific optimization steps (Core, Shadows, Lighting, Stripping, Audio/Physics).

## 3. Core Technical Questions
- Does enforcing Vulkan on Android provide enough CPU benefit to outweigh driver instability and WebView context-switching risks?
- How can ambient lighting and fog be stripped without shifting UI material hex-colors or making elements disappear?
- What are the hidden causes of main-thread stalls (ANRs) during heavy UI loading or Ad transitions?
- How can memory pressure be reduced efficiently without touching visual asset resolutions?

## 4. Key Decisions and Conclusions
- **Decision:** Force Android Graphics API to OpenGLES3 strictly (Remove Vulkan).
  - **Why it was chosen:** Vulkan drivers on 3-to-4-year-old budget Android devices are prone to native crashes (SIGSEGV) during memory allocation. Furthermore, switching contexts between a Vulkan-rendered game and a GLES/Software-rendered Ad WebView frequently causes deadlocks and ANRs.
  - **Benefits:** Massively reduces ANR rates and black-screen issues post-ad playback.
  - **Costs / tradeoffs:** Slight CPU overhead in high draw-call scenarios (negligible for UI-heavy batched projects).
  - **When this decision is valid:** Projects monetized via WebView-based Ads targeting a broad, mid-to-low-end Android demographic.
  - **Confidence:** High.

- **Decision:** Set Ambient Light to `Color.white` with Intensity `1.0f` and Ambient Mode to `Flat`.
  - **Why it was chosen:** If any UI materials accidentally use a Lit shader, a Black ambient light would render them invisible. White ambient ensures `Albedo * 1.0 = True Color`, perfectly matching Figma.
  - **Benefits:** Strips lighting pass cost while guaranteeing UI color fidelity.
  - **Confidence:** High.

- **Decision:** Increase `asyncUploadBufferSize` from 16MB to 64MB and `asyncUploadTimeSlice` from 2ms to 4ms.
  - **Why it was chosen:** 16MB is too small for modern UI atlases. If an asset exceeds the buffer, Unity falls back to synchronous main-thread loading, causing a 100-300ms stutter (ANR risk during Ad SDK transitions).
  - **Confidence:** High.

- **Decision:** Disable Mipmaps on all UI Sprites.
  - **Why it was chosen:** 2D UI is typically rendered 1:1 or close to the camera. Mipmaps waste ~33% VRAM per texture.
  - **Confidence:** High.

- **Decision:** Force `Streaming` Load Type for Audio Clips > 500KB; Force `Mono` for UI SFX.
  - **Why it was chosen:** Long tracks set to `DecompressOnLoad` expand drastically in RAM (e.g., 1MB MP3 -> 10MB PCM), risking LMK termination. Stereo UI clicks waste CPU mixing cycles.
  - **Confidence:** High.

## 5. Rejected or Dangerous Alternatives
- **Alternative / simplification:** Disabling `DepthTextureMode` on all cameras to save GPU bandwidth.
  - **Why it looked attractive:** Standard unlit 2D UI does not need depth textures.
  - **Why it was rejected or considered dangerous:** MRAID video ad players and certain Ad SDK overlays rely on depth buffers for correct z-ordering. Stripping it globally breaks ad rendering.
  - **Final stance:** Rejected. Ad-stack/overlay cameras must be explicitly filtered and protected from graphic optimizations.

- **Alternative / simplification:** Applying global ASTC 6x6 or 8x8 compression to all textures.
  - **Why it looked attractive:** Massive reduction in build size and VRAM usage.
  - **Why it was rejected or considered dangerous:** Blocks >= 6x6 introduce severe ringing and blur artifacts on sharp UI edges and text.
  - **Final stance:** Context-dependent. Implemented a "Texture Guard" to scan and warn against ASTC 6x6+ specifically on UI sprites.

- **Alternative / simplification:** Setting `QualitySettings.lodBias` to a low value (e.g., `0.3`) to aggressively cull geometry.
  - **Why it looked attractive:** Standard 3D optimization practice.
  - **Why it was rejected or considered dangerous:** Causes Unity to downsample UI textures, leading to blurry canvases.
  - **Final stance:** Rejected. Enforced `lodBias = 1.0f` for UI crispness.

## 6. Critical Risks and Failure Modes

- **Risk:** Main-Thread Ad Context Deadlock (ANR)
  - **Trigger scenario:** User closes a heavy Playable Ad (WebView) and the OS attempts to restore the Unity rendering context on a low-end Vulkan driver.
  - **Impact:** Application freezes, resulting in an ANR.
  - **Severity:** High
  - **Mitigation:** Enforce OpenGLES3 on Android.

- **Risk:** Out of Memory (OOM) Crash during Ad transition
  - **Trigger scenario:** Ad SDK loads a heavy video into memory while Unity holds large uncompressed Audio files (`DecompressOnLoad`) and UI Mipmaps in RAM.
  - **Impact:** Android LMK kills the app.
  - **Severity:** High
  - **Mitigation:** Force UI Mipmaps off; force large audio to `Streaming`; clear Lightmap data (`Lightmapping.Clear()`).

- **Risk:** UI Input Lag / CPU Spikes
  - **Trigger scenario:** Hundreds of nested Figma-imported UI elements have `RaycastTarget = true` by default. EventSystem iterates all of them on every touch.
  - **Impact:** Micro-stutters during user interaction.
  - **Severity:** Medium
  - **Mitigation:** Scripted audit to flag/disable `RaycastTarget` on non-interactive graphics.

- **Risk:** Render Batching breakage (Mask Hell)
  - **Trigger scenario:** Designers use standard `Mask` components for rectangular clipping (e.g., scroll views).
  - **Impact:** Introduces Stencil buffer passes, breaking SRP/Dynamic batching and increasing Draw Calls.
  - **Severity:** Medium
  - **Mitigation:** Audit and replace standard `Mask` with `RectMask2D` where appropriate.

## 7. Reviewer Checklist
- **Reject if** the Android Graphics API is set to Vulkan for UI/Ad-heavy applications targeting tier-2/3 demographics.
- **Reject if** overlay or stacking cameras (`ClearFlags.Depth` or `ClearFlags.Nothing`) have their settings stripped or modified by global optimizer scripts.
- **Verify that** `asyncUploadBufferSize` is >= 64MB to prevent synchronous loading stalls.
- **Add tests for** UI window instantiation to ensure no main-thread spikes > 32ms (check `ShaderPreload` arrays).
- **Require proof that** any UI Sprite using ASTC compression >= 6x6 does not exhibit visual degradation.
- **Safe only if** Ambient Light is set to White (not Black) when stripping lighting to preserve Albedo matching.

## 8. Testing Strategy and Required Coverage
- **State / lifecycle behavior:** 
  - Rapidly open/close Ad overlays. Verify successful context restoration and absence of black screens on Android GLES3.
- **Happy path (Visuals):**
  - Compare side-by-side Unity Canvas renders vs. Figma designs to verify Linear/Gamma and White Ambient settings maintain hex parity.
- **Performance / Memory:**
  - Monitor memory baseline before and after disabling UI Sprite Mipmaps and setting Audio to Streaming.
- **Fast synchronous completion:**
  - Open the heaviest UI prefab. Ensure `asyncUploadBufferSize` accommodates the atlas without stalling the main thread.

## 9. Reusable Engineering Principles
- **Context-Switching Cost Overrides CPU Gains:** A lower-level API (Vulkan) is harmful if it conflicts with OS-level components (WebView) that dominate the app's monetization flow.
- **Invisible Workload Elimination:** Systems like physics (AutoSyncTransforms), sensors (Accelerometer polling), and Audio (Doppler math, Stereo mixing) consume CPU cycles even in "2D" states. Explicitly disabling them raises the thermal throttling ceiling.
- **Memory Defines Stability:** On mobile, OOM is a far more common crash cause than logic exceptions. Stripping Mipmaps from 1:1 UI assets and streaming large audio are non-negotiable memory guards.

## 10. Open Questions and Uncertainties
- **Garbage Collection:** What is the optimal IL2CPP GC configuration (e.g., Incremental GC vs standard) during Ad playback to avoid stutters?
- **Scripting Backend:** Are there specific IL2CPP compiler flags that should be tuned for pure UI performance?

## 11. Final Reviewer Handoff
- **Safest implementation direction:** Modularize all Editor-time optimizations so they can be A/B tested in builds (Core -> Shadows -> Lighting -> Memory).
- **Most dangerous area:** Modifying `Camera` and `QualitySettings` globally without filtering out Ad SDK overlay cameras or buffer requirements.
- **Most important invariant:** Android must remain on OpenGLES3; UI Textures must not use Mipmaps.
- **Easiest wrong simplification:** Setting Ambient Light to Black to "disable" lighting (which silently breaks any UI material with a Lit shader).
- **Minimum required test coverage before production use:** Ad playback cycle on a low-end Android device (e.g., Samsung A10/A20) to ensure zero ANRs and successful graphical context restoration.