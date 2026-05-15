using NUnit.Framework;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;
using XUUnity.LightMcp.Editor.Helpers;
using XUUnity.LightMcp.Editor.Operations;

namespace XUUnity.LightMcp.Tests.EditMode
{
    [Category("XUUnity.MCP.SelfTest")]
    [Category("XUUnity.MCP.EditMode")]
    [Category("XUUnity.MCP.Fast")]
    public sealed class XUUnityLightMcpEditModeSelfTests
    {
        GameObject _createdRoot;

        [TearDown]
        public void TearDown()
        {
            if (_createdRoot != null)
            {
                Object.DestroyImmediate(_createdRoot);
                _createdRoot = null;
            }
        }

        [Test]
        public void TestFilter_NormalizesEmptyAndDuplicateValues()
        {
            var values = XUUnityLightMcpTestsUtility.NormalizeOptionalStringArray(
                new[] { "", "  alpha  ", "alpha", "beta", "  " });

            CollectionAssert.AreEqual(new[] { "alpha", "beta" }, values);
        }

        [Test]
        public void TestFilter_BuildsCategoryAndAssemblyFilter()
        {
            var args = JsonUtility.ToJson(new XUUnityLightMcpTestsArgs
            {
                categoryNames = new[] { "XUUnity.MCP.Fast" },
                assemblyNames = new[] { "com.xuunity.light-mcp.Editor.Tests" }
            });

            var built = XUUnityLightMcpTestsUtility.TryBuildFilter(
                args,
                TestMode.EditMode,
                "EditMode",
                out var filter,
                out var summary,
                out var errorMessage);

            Assert.That(built, Is.True, errorMessage);
            Assert.That(filter.testMode, Is.EqualTo(TestMode.EditMode));
            CollectionAssert.AreEqual(new[] { "XUUnity.MCP.Fast" }, filter.categoryNames);
            CollectionAssert.AreEqual(new[] { "com.xuunity.light-mcp.Editor.Tests" }, filter.assemblyNames);
            Assert.That(summary, Does.Contain("categories=XUUnity.MCP.Fast"));
        }

        [Test]
        public void ResponseWriter_SuccessAndErrorPreserveRequestContract()
        {
            var success = XUUnityLightMcpResponseWriter.Success("req-1", "unity.selftest", "{\"ok\":true}");
            var error = XUUnityLightMcpResponseWriter.Error("req-2", "selftest_failed", "Failure message.");

            Assert.That(success.request_id, Is.EqualTo("req-1"));
            Assert.That(success.status, Is.EqualTo("ok"));
            Assert.That(success.payload_type, Is.EqualTo("unity.selftest"));
            Assert.That(success.payload_json, Does.Contain("\"ok\":true"));
            Assert.That(success.error, Is.Null);
            Assert.That(error.request_id, Is.EqualTo("req-2"));
            Assert.That(error.status, Is.EqualTo("error"));
            Assert.That(error.error.code, Is.EqualTo("selftest_failed"));
            Assert.That(error.error.message, Is.EqualTo("Failure message."));
        }

        [Test]
        [Category("XUUnity.MCP.Scene")]
        public void SceneSnapshotOperation_ReportsRootGameObjectNames()
        {
            _createdRoot = new GameObject("XUUnityMcp_EditModeSnapshotRoot");

            var response = new XUUnityLightMcpSceneSnapshotOperation().Execute(new XUUnityLightMcpRequest
            {
                request_id = "scene-snapshot-selftest",
                operation = "unity.scene.snapshot",
                args_json = "{}"
            });
            var payload = JsonUtility.FromJson<XUUnityLightMcpSceneSnapshotPayload>(response.payload_json);

            Assert.That(response.status, Is.EqualTo("ok"));
            Assert.That(payload.active_scene.root_count, Is.GreaterThanOrEqualTo(1));
            Assert.That(
                payload.root_objects.Exists(root => root.name == "XUUnityMcp_EditModeSnapshotRoot"),
                Is.True);
        }

        [Test]
        [Category("XUUnity.MCP.Scene")]
        public void SceneAssertOperation_ReportsMissingRequiredRoots()
        {
            _createdRoot = new GameObject("XUUnityMcp_EditModeAssertRoot");
            var args = JsonUtility.ToJson(new XUUnityLightMcpSceneAssertArgs
            {
                allowDirty = true,
                requiredRootNames = new[]
                {
                    "XUUnityMcp_EditModeAssertRoot",
                    "XUUnityMcp_MissingRoot"
                }
            });

            var response = new XUUnityLightMcpSceneAssertOperation().Execute(new XUUnityLightMcpRequest
            {
                request_id = "scene-assert-selftest",
                operation = "unity.scene.assert",
                args_json = args
            });
            var payload = JsonUtility.FromJson<XUUnityLightMcpSceneAssertPayload>(response.payload_json);

            Assert.That(response.status, Is.EqualTo("ok"));
            Assert.That(payload.status, Is.EqualTo("failed"));
            CollectionAssert.Contains(payload.missing_root_names, "XUUnityMcp_MissingRoot");
            Assert.That(payload.failure_reason, Does.Contain("XUUnityMcp_MissingRoot"));
        }

        [Test]
        public void StatusOperation_ReturnsEditorStatePayload()
        {
            var response = new XUUnityLightMcpStatusOperation().Execute(new XUUnityLightMcpRequest
            {
                request_id = "status-selftest",
                operation = "unity.status",
                args_json = "{}"
            });
            var payload = JsonUtility.FromJson<XUUnityLightMcpStatusPayload>(response.payload_json);

            Assert.That(response.status, Is.EqualTo("ok"));
            Assert.That(payload.project_root, Is.Not.Empty);
            Assert.That(payload.playmode_state, Is.Not.Empty);
            Assert.That(payload.health_status, Is.Not.Empty);
            Assert.That(payload.supported_operations, Does.Contain("unity.status"));
        }
    }
}
