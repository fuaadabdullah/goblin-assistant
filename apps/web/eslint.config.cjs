const tsParser = require("@typescript-eslint/parser");
const tsPlugin = require("@typescript-eslint/eslint-plugin");
const reactHooksPlugin = require("eslint-plugin-react-hooks");

module.exports = [
    {
        ignores: [
            ".next/**",
            "node_modules/**",
            "dist/**",
            "coverage/**",
            "public/**",
            ".git/**",
            ".vercel/**",
            "**/._*",
            "**/*.stories.*",
            "tests/test_connection.js",
            "tests/legacy/**",
        ],
    },
    {
        files: ["**/*.{js,jsx}"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                console: "readonly",
                fetch: "readonly",
                window: "readonly",
                document: "readonly",
                process: "readonly",
                require: "readonly",
                module: "readonly",
                exports: "readonly",
            },
        },
        plugins: {
            "react-hooks": reactHooksPlugin,
        },
        rules: {
            "react-hooks/exhaustive-deps": "warn",
            "max-lines-per-function": ["warn", { max: 40, skipBlankLines: true, skipComments: true }],
            "max-depth": ["warn", 3],
            complexity: ["warn", 10],
        },
    },
    {
        files: ["**/*.{ts,tsx}"],
        languageOptions: {
            parser: tsParser,
            parserOptions: {
                ecmaVersion: "latest",
                sourceType: "module",
                ecmaFeatures: {
                    jsx: true,
                },
            },
            globals: {
                console: "readonly",
                fetch: "readonly",
                window: "readonly",
                document: "readonly",
                process: "readonly",
                require: "readonly",
                module: "readonly",
                exports: "readonly",
            },
        },
        plugins: {
            "@typescript-eslint": tsPlugin,
            "react-hooks": reactHooksPlugin,
        },
        rules: {
            "@typescript-eslint/no-var-requires": "warn",
            "@typescript-eslint/no-explicit-any": "warn",
            "@typescript-eslint/naming-convention": [
                "warn",
                {
                    selector: "variableLike",
                    format: ["camelCase", "UPPER_CASE", "PascalCase"],
                },
                {
                    selector: "typeLike",
                    format: ["PascalCase"],
                },
                {
                    selector: "function",
                    format: ["camelCase", "PascalCase"],
                },
            ],
            "react-hooks/exhaustive-deps": "warn",
            "max-lines-per-function": ["warn", { max: 40, skipBlankLines: true, skipComments: true }],
            "max-depth": ["warn", 3],
            complexity: ["warn", 10],
            "no-restricted-syntax": [
                "warn",
                {
                    selector: "VariableDeclarator[id.name=/^(data|temp|helper|manager)$/]",
                    message: "Use intent-revealing names such as pendingOrders or riskEngine.",
                },
                {
                    selector: "FunctionDeclaration[id.name='process']",
                    message: "Use a specific verb name instead of process().",
                },
                {
                    selector: "FunctionExpression[id.name='process']",
                    message: "Use a specific verb name instead of process().",
                },
                {
                    selector: "ArrowFunctionExpression[id.name='process']",
                    message: "Use a specific verb name instead of process().",
                },
            ],
        },
    },
    {
        files: ["src/utils/**/*.{ts,tsx,js,jsx}", "src/lib/**/*.{ts,tsx,js,jsx}"],
        rules: {
            "no-restricted-globals": [
                "warn",
                {
                    name: "fetch",
                    message:
                        "Avoid direct network calls in pure utility/core modules. Move I/O to boundary layers.",
                },
            ],
        },
    },
    {
        files: ["src/features/**/components/**/*.{ts,tsx}"],
        rules: {
            "no-restricted-imports": [
                "warn",
                {
                    paths: [
                        {
                            name: "@/api",
                            message: "Do not call API client from presentational components. Use feature hooks/services.",
                        },
                    ],
                },
            ],
        },
    },
];
