using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using XUUnity.LightMcp.Editor.Core;

namespace XUUnity.LightMcp.Editor.Operations
{
    internal sealed class XUUnityLightMcpSdkDependencyVerifyOperation : IXUUnityLightMcpOperation
    {
        public string OperationName => "unity.sdk.dependency.verify";

        public XUUnityLightMcpResponse Execute(XUUnityLightMcpRequest request)
        {
            var args = string.IsNullOrWhiteSpace(request.args_json)
                ? new XUUnityLightMcpSdkDependencyVerifyArgs()
                : JsonUtility.FromJson<XUUnityLightMcpSdkDependencyVerifyArgs>(request.args_json) ?? new XUUnityLightMcpSdkDependencyVerifyArgs();

            try
            {
                var payload = new XUUnityLightMcpSdkDependencyVerifyPayload
                {
                    project_root = XUUnityLightMcpFileIpcPaths.ProjectRootPath,
                    stop_on_first_failure = args.stopOnFirstFailure,
                };

                if (args.expectations == null || args.expectations.Count == 0)
                {
                    return XUUnityLightMcpResponseWriter.Error(
                        request.request_id,
                        "missing_expectations",
                        "unity.sdk.dependency.verify requires at least one expectation.");
                }

                foreach (var expectation in args.expectations)
                {
                    var result = VerifyExpectation(expectation ?? new XUUnityLightMcpSdkDependencyExpectation());
                    payload.results.Add(result);

                    if (result.status == "passed")
                    {
                        payload.passed++;
                    }
                    else if (result.status == "skipped")
                    {
                        payload.skipped++;
                    }
                    else
                    {
                        payload.failed++;
                    }

                    if (args.stopOnFirstFailure && result.status == "failed")
                    {
                        break;
                    }
                }

                payload.total = payload.results.Count;
                payload.status = payload.failed == 0 ? "passed" : "failed";

                return XUUnityLightMcpResponseWriter.Success(
                    request.request_id,
                    OperationName,
                    JsonUtility.ToJson(payload));
            }
            catch (Exception ex)
            {
                return XUUnityLightMcpResponseWriter.Error(request.request_id, "sdk_dependency_verify_failed", ex.Message);
            }
        }

        static XUUnityLightMcpSdkDependencyVerifyResult VerifyExpectation(XUUnityLightMcpSdkDependencyExpectation expectation)
        {
            var result = new XUUnityLightMcpSdkDependencyVerifyResult
            {
                id = expectation.id ?? "",
                platform = expectation.platform ?? "",
                path = expectation.path ?? "",
                kind = NormalizeKind(expectation.kind),
                value = expectation.value ?? "",
                expected_version = expectation.version ?? "",
                expected_min_version = expectation.minVersion ?? "",
            };

            if (string.IsNullOrWhiteSpace(expectation.path))
            {
                return Fail(result, "Expectation path is required.");
            }

            if (!TryResolveProjectFile(expectation.path, out var fullPath, out var pathError))
            {
                result.full_path = fullPath ?? "";
                return Fail(result, pathError);
            }

            result.full_path = fullPath;
            result.file_exists = File.Exists(fullPath);
            if (!result.file_exists)
            {
                return expectation.optional
                    ? Skip(result, "Optional file is missing.")
                    : Fail(result, "Expected file is missing.");
            }

            var info = new FileInfo(fullPath);
            result.file_size_bytes = info.Length;
            result.sha256 = ComputeSha256(fullPath);

            var content = File.ReadAllText(fullPath);
            return result.kind switch
            {
                "file_contains" => CheckContains(result, content, result.value),
                "file_regex" => CheckRegex(result, content, result.value),
                "android_resolver_package" => CheckAndroidResolverPackage(result, content),
                "gradle_dependency" => CheckContains(result, content, result.value),
                "gradle_repository" => CheckContains(result, content, result.value),
                "podfile_lock_pod" => CheckPodfileLockPod(result, content),
                _ => Fail(result, $"Unsupported dependency verification kind '{result.kind}'."),
            };
        }

        static string NormalizeKind(string kind)
        {
            return string.IsNullOrWhiteSpace(kind) ? "file_contains" : kind.Trim().ToLowerInvariant();
        }

        static XUUnityLightMcpSdkDependencyVerifyResult CheckContains(
            XUUnityLightMcpSdkDependencyVerifyResult result,
            string content,
            string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return Fail(result, "Expected value is required.");
            }

            return content.Contains(value, StringComparison.Ordinal)
                ? Pass(result, "Expected value found.")
                : Fail(result, "Expected value was not found.");
        }

        static XUUnityLightMcpSdkDependencyVerifyResult CheckRegex(
            XUUnityLightMcpSdkDependencyVerifyResult result,
            string content,
            string pattern)
        {
            if (string.IsNullOrWhiteSpace(pattern))
            {
                return Fail(result, "Regex pattern is required.");
            }

            return Regex.IsMatch(content, pattern, RegexOptions.Multiline)
                ? Pass(result, "Expected regex matched.")
                : Fail(result, "Expected regex did not match.");
        }

        static XUUnityLightMcpSdkDependencyVerifyResult CheckAndroidResolverPackage(
            XUUnityLightMcpSdkDependencyVerifyResult result,
            string content)
        {
            if (string.IsNullOrWhiteSpace(result.value))
            {
                return Fail(result, "Expected Android package spec is required.");
            }

            var expectedNode = $"<package>{result.value}</package>";
            if (content.Contains(expectedNode, StringComparison.Ordinal) || content.Contains(result.value, StringComparison.Ordinal))
            {
                return Pass(result, "Expected Android resolver package found.");
            }

            return Fail(result, "Expected Android resolver package was not found.");
        }

        static XUUnityLightMcpSdkDependencyVerifyResult CheckPodfileLockPod(
            XUUnityLightMcpSdkDependencyVerifyResult result,
            string content)
        {
            if (string.IsNullOrWhiteSpace(result.value))
            {
                return Fail(result, "Expected pod name is required.");
            }

            var pattern = @"-\s+" + Regex.Escape(result.value) + @"\s+\(([^)]+)\)";
            var match = Regex.Match(content, pattern);
            if (!match.Success)
            {
                return Fail(result, "Expected pod was not found.");
            }

            result.actual_version = NormalizeVersion(match.Groups[1].Value);
            if (!string.IsNullOrWhiteSpace(result.expected_version)
                && !string.Equals(result.actual_version, NormalizeVersion(result.expected_version), StringComparison.Ordinal))
            {
                return Fail(result, $"Pod version mismatch. Actual '{result.actual_version}'.");
            }

            if (!string.IsNullOrWhiteSpace(result.expected_min_version)
                && CompareVersions(result.actual_version, result.expected_min_version) < 0)
            {
                return Fail(result, $"Pod version '{result.actual_version}' is lower than minimum '{result.expected_min_version}'.");
            }

            return Pass(result, "Expected pod version found.");
        }

        static string NormalizeVersion(string value)
        {
            return (value ?? "").Trim().TrimStart('=').Trim();
        }

        static int CompareVersions(string left, string right)
        {
            var leftParts = NormalizeVersion(left).Split('.');
            var rightParts = NormalizeVersion(right).Split('.');
            var max = Math.Max(leftParts.Length, rightParts.Length);
            for (var i = 0; i < max; i++)
            {
                var leftValue = ParseVersionPart(leftParts, i);
                var rightValue = ParseVersionPart(rightParts, i);
                if (leftValue != rightValue)
                {
                    return leftValue.CompareTo(rightValue);
                }
            }

            return 0;
        }

        static int ParseVersionPart(string[] parts, int index)
        {
            if (parts == null || index >= parts.Length)
            {
                return 0;
            }

            var match = Regex.Match(parts[index] ?? "", @"\d+");
            return match.Success && int.TryParse(match.Value, out var value) ? value : 0;
        }

        static bool TryResolveProjectFile(string path, out string fullPath, out string error)
        {
            fullPath = "";
            error = "";

            try
            {
                var projectRoot = Path.GetFullPath(XUUnityLightMcpFileIpcPaths.ProjectRootPath);
                fullPath = Path.IsPathRooted(path)
                    ? Path.GetFullPath(path)
                    : Path.GetFullPath(Path.Combine(projectRoot, path));

                var rootWithSeparator = projectRoot.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal)
                    ? projectRoot
                    : projectRoot + Path.DirectorySeparatorChar;

                if (!string.Equals(fullPath, projectRoot, StringComparison.Ordinal)
                    && !fullPath.StartsWith(rootWithSeparator, StringComparison.Ordinal))
                {
                    error = "Expectation path must resolve inside the Unity project root.";
                    return false;
                }

                return true;
            }
            catch (Exception ex)
            {
                error = ex.Message;
                return false;
            }
        }

        static string ComputeSha256(string path)
        {
            using var sha = SHA256.Create();
            using var stream = File.OpenRead(path);
            var hash = sha.ComputeHash(stream);
            var builder = new StringBuilder(hash.Length * 2);
            foreach (var b in hash)
            {
                builder.Append(b.ToString("x2"));
            }

            return builder.ToString();
        }

        static XUUnityLightMcpSdkDependencyVerifyResult Pass(XUUnityLightMcpSdkDependencyVerifyResult result, string message)
        {
            result.status = "passed";
            result.message = message;
            return result;
        }

        static XUUnityLightMcpSdkDependencyVerifyResult Skip(XUUnityLightMcpSdkDependencyVerifyResult result, string message)
        {
            result.status = "skipped";
            result.message = message;
            return result;
        }

        static XUUnityLightMcpSdkDependencyVerifyResult Fail(XUUnityLightMcpSdkDependencyVerifyResult result, string message)
        {
            result.status = "failed";
            result.message = message;
            return result;
        }
    }
}
