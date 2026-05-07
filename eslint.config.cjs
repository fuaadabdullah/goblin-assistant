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
            "react-hooks/exhaustive-deps": "warn",
        },
    },
];
