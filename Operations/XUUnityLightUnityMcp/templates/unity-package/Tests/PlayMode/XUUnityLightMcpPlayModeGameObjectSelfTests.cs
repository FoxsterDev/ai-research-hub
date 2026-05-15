using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace XUUnity.LightMcp.Tests.PlayMode
{
    [Category("XUUnity.MCP.SelfTest")]
    [Category("XUUnity.MCP.PlayMode")]
    [Category("XUUnity.MCP.Fast")]
    public sealed class XUUnityLightMcpPlayModeGameObjectSelfTests
    {
        GameObject _createdRoot;

        [TearDown]
        public void TearDown()
        {
            if (_createdRoot != null)
            {
                Object.Destroy(_createdRoot);
                _createdRoot = null;
            }
        }

        [UnityTest]
        [Category("XUUnity.MCP.GameObject")]
        [Category("XUUnity.MCP.Lifecycle")]
        public IEnumerator GameObjectLifecycle_InvokesAwakeEnableAndStart()
        {
            _createdRoot = new GameObject("XUUnityMcp_PlayModeLifecycleRoot");
            var probe = _createdRoot.AddComponent<LifecycleProbe>();

            yield return null;

            Assert.That(probe.awakeCount, Is.EqualTo(1));
            Assert.That(probe.enableCount, Is.EqualTo(1));
            Assert.That(probe.startCount, Is.EqualTo(1));
            Assert.That(probe.isActiveAndEnabled, Is.True);
        }

        [UnityTest]
        [Category("XUUnity.MCP.Coroutine")]
        public IEnumerator CoroutineProgress_MutatesStateAcrossFrames()
        {
            _createdRoot = new GameObject("XUUnityMcp_PlayModeCoroutineRoot");
            var probe = _createdRoot.AddComponent<CoroutineProbe>();

            probe.Begin();
            yield return null;
            yield return null;
            yield return null;

            Assert.That(probe.completed, Is.True);
            Assert.That(probe.frameCount, Is.GreaterThanOrEqualTo(2));
        }

        [Test]
        [Category("XUUnity.MCP.GameObject")]
        public void TransformHierarchy_ReparentingPreservesWorldPosition()
        {
            _createdRoot = new GameObject("XUUnityMcp_PlayModeHierarchyRoot");
            var child = new GameObject("XUUnityMcp_PlayModeHierarchyChild");
            child.transform.position = new Vector3(2.0f, 3.0f, 4.0f);
            child.transform.SetParent(_createdRoot.transform, true);

            Assert.That(child.transform.parent, Is.EqualTo(_createdRoot.transform));
            Assert.That(child.transform.position, Is.EqualTo(new Vector3(2.0f, 3.0f, 4.0f)));
            Assert.That(_createdRoot.transform.childCount, Is.EqualTo(1));
        }

        [UnityTest]
        [Category("XUUnity.MCP.Scene")]
        public IEnumerator SceneApi_CanCreateSetActiveAndUnloadTemporaryScene()
        {
            var originalScene = SceneManager.GetActiveScene();
            var testScene = SceneManager.CreateScene("XUUnityMcp_PlayModeTemporaryScene");
            _createdRoot = new GameObject("XUUnityMcp_PlayModeSceneRoot");
            SceneManager.MoveGameObjectToScene(_createdRoot, testScene);

            Assert.That(SceneManager.SetActiveScene(testScene), Is.True);
            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo("XUUnityMcp_PlayModeTemporaryScene"));
            Assert.That(testScene.GetRootGameObjects(), Has.Exactly(1).Matches<GameObject>(
                root => root.name == "XUUnityMcp_PlayModeSceneRoot"));

            Object.Destroy(_createdRoot);
            _createdRoot = null;
            yield return SceneManager.UnloadSceneAsync(testScene);

            if (originalScene.IsValid() && originalScene.isLoaded)
            {
                SceneManager.SetActiveScene(originalScene);
            }
        }

        [UnityTest]
        [Category("XUUnity.MCP.Lifecycle")]
        public IEnumerator DontDestroyOnLoad_ObjectRemainsUsableUntilExplicitCleanup()
        {
            _createdRoot = new GameObject("XUUnityMcp_PlayModePersistentRoot");
            Object.DontDestroyOnLoad(_createdRoot);

            yield return null;

            Assert.That(_createdRoot, Is.Not.Null);
            Assert.That(_createdRoot.activeInHierarchy, Is.True);
            Assert.That(_createdRoot.scene.IsValid(), Is.True);
        }

        sealed class LifecycleProbe : MonoBehaviour
        {
            public int awakeCount;
            public int enableCount;
            public int startCount;

            void Awake()
            {
                awakeCount++;
            }

            void OnEnable()
            {
                enableCount++;
            }

            void Start()
            {
                startCount++;
            }
        }

        sealed class CoroutineProbe : MonoBehaviour
        {
            public bool completed;
            public int frameCount;

            public void Begin()
            {
                StartCoroutine(Run());
            }

            IEnumerator Run()
            {
                frameCount++;
                yield return null;
                frameCount++;
                yield return null;
                completed = true;
            }
        }
    }
}
