using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEditor.TestTools.TestRunner.Api;

namespace XUUnity.LightMcp.Editor.Helpers
{
    internal static class XUUnityLightMcpEditModeFilterResolver
    {
        static readonly HashSet<string> SupportedMethodAttributeNames = new(StringComparer.Ordinal)
        {
            "NUnit.Framework.TestAttribute",
            "NUnit.Framework.TestCaseAttribute",
            "NUnit.Framework.TestCaseSourceAttribute",
            "NUnit.Framework.TheoryAttribute",
            "UnityEngine.TestTools.UnityTestAttribute"
        };

        public static void ResolveTestNames(Filter filter)
        {
            if (filter == null)
            {
                return;
            }

            filter.testNames = ResolveTestNames(filter.testNames, filter.assemblyNames);
        }

        static string[] ResolveTestNames(string[] requestedTestNames, string[] assemblyNames)
        {
            var normalizedRequestedNames = NormalizeFilterValues(requestedTestNames);
            if (normalizedRequestedNames == null)
            {
                return null;
            }

            var catalog = BuildTestCatalog(assemblyNames);
            if (catalog.Count == 0)
            {
                return normalizedRequestedNames;
            }

            var resolved = new List<string>(normalizedRequestedNames.Length);
            foreach (var requestedName in normalizedRequestedNames)
            {
                if (catalog.TryGetValue(requestedName, out var matches))
                {
                    resolved.AddRange(matches);
                    continue;
                }

                resolved.Add(requestedName);
            }

            return resolved
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Distinct(StringComparer.Ordinal)
                .ToArray();
        }

        static Dictionary<string, List<string>> BuildTestCatalog(string[] assemblyNames)
        {
            var catalog = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            var requestedAssemblies = NormalizeFilterValues(assemblyNames);
            var assemblyFilter = requestedAssemblies == null
                ? null
                : new HashSet<string>(requestedAssemblies, StringComparer.OrdinalIgnoreCase);

            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (assembly == null || assembly.IsDynamic)
                {
                    continue;
                }

                var assemblyName = assembly.GetName().Name;
                if (assemblyFilter != null && !assemblyFilter.Contains(assemblyName))
                {
                    continue;
                }

                foreach (var type in GetLoadableTypes(assembly))
                {
                    if (type == null || string.IsNullOrWhiteSpace(type.FullName))
                    {
                        continue;
                    }

                    var leafTestNames = GetLeafTestNames(type);
                    if (leafTestNames.Count == 0)
                    {
                        continue;
                    }

                    var normalizedTypeFullName = NormalizeTypeName(type.FullName);
                    AddMatches(catalog, type.Name, leafTestNames);
                    AddMatches(catalog, normalizedTypeFullName, leafTestNames);

                    foreach (var leafTestName in leafTestNames)
                    {
                        var shortMethodName = leafTestName.Substring(normalizedTypeFullName.Length + 1);
                        AddMatches(catalog, shortMethodName, leafTestName);
                        AddMatches(catalog, $"{type.Name}.{shortMethodName}", leafTestName);
                        AddMatches(catalog, $"{normalizedTypeFullName}.{shortMethodName}", leafTestName);
                    }
                }
            }

            return catalog;
        }

        static IReadOnlyList<Type> GetLoadableTypes(Assembly assembly)
        {
            try
            {
                return assembly.GetTypes();
            }
            catch (ReflectionTypeLoadException ex)
            {
                return ex.Types.Where(type => type != null).ToArray();
            }
            catch
            {
                return Array.Empty<Type>();
            }
        }

        static List<string> GetLeafTestNames(Type type)
        {
            var normalizedTypeFullName = NormalizeTypeName(type.FullName);
            var result = new List<string>();

            foreach (var method in type.GetMethods(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (method == null || method.IsSpecialName || !IsLeafTestMethod(method))
                {
                    continue;
                }

                result.Add($"{normalizedTypeFullName}.{method.Name}");
            }

            return result
                .Distinct(StringComparer.Ordinal)
                .ToList();
        }

        static bool IsLeafTestMethod(MemberInfo method)
        {
            return method
                .GetCustomAttributesData()
                .Any(attributeData => SupportedMethodAttributeNames.Contains(attributeData.AttributeType.FullName));
        }

        static string NormalizeTypeName(string typeName)
        {
            return string.IsNullOrWhiteSpace(typeName)
                ? string.Empty
                : typeName.Replace('+', '.');
        }

        static string[] NormalizeFilterValues(string[] values)
        {
            if (values == null || values.Length == 0)
            {
                return null;
            }

            var normalized = values
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Select(value => value.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();

            return normalized.Length == 0 ? null : normalized;
        }

        static void AddMatches(Dictionary<string, List<string>> catalog, string key, IEnumerable<string> matches)
        {
            if (string.IsNullOrWhiteSpace(key))
            {
                return;
            }

            if (!catalog.TryGetValue(key, out var existing))
            {
                existing = new List<string>();
                catalog[key] = existing;
            }

            foreach (var match in matches)
            {
                AddMatch(existing, match);
            }
        }

        static void AddMatches(Dictionary<string, List<string>> catalog, string key, string match)
        {
            if (string.IsNullOrWhiteSpace(key) || string.IsNullOrWhiteSpace(match))
            {
                return;
            }

            if (!catalog.TryGetValue(key, out var existing))
            {
                existing = new List<string>();
                catalog[key] = existing;
            }

            AddMatch(existing, match);
        }

        static void AddMatch(List<string> matches, string match)
        {
            if (matches.Contains(match, StringComparer.Ordinal))
            {
                return;
            }

            matches.Add(match);
        }
    }
}
