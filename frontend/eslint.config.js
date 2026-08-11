// ESLint flat config（v9+）：Vue 3 + TypeScript 项目的轻量 lint 防线。
// 设计意图：typecheck（vue-tsc）负责类型，eslint 负责未使用变量/导入、
// 未定义变量等代码卫生问题；规则保持保守，避免与既有代码风格冲突。
import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
import vueParser from "vue-eslint-parser";

export default tseslint.config(
  { ignores: ["dist/**", "node_modules/**", "coverage/**"] },
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: [".vue"],
        sourceType: "module",
      },
    },
  },
  {
    files: ["**/*.{ts,vue}"],
    rules: {
      // 未使用变量与导入：清理死代码的第一道防线。
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "off",
      // 关闭与 prettier/vue-tsc 重叠或过于严格的规则，避免噪音。
      "vue/multi-word-component-names": "off",
      "vue/require-default-prop": "off",
      "vue/singleline-html-element-content-newline": "off",
    },
  },
);
