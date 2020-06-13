module.exports = {
  plugins: ['json', 'react', 'prettier', '@typescript-eslint', 'react-hooks', 'import'],
  parser: '@typescript-eslint/parser',
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/eslint-recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:prettier/recommended',
    'prettier/@typescript-eslint',
    'prettier/react',
    'plugin:import/typescript',
  ],
  parserOptions: {
    ecmaVersion: 2018,
    sourceType: 'module',
  },
  rules: {
    'no-undef': 'off',
    'react/prop-types': 'off',
    'react/display-name': 'off',
    '@typescript-eslint/interface-name-prefix': 'off',
    'no-unused-vars': ['error', { args: 'none' }],
    'no-unused-expressions': ['error', { 'allowShortCircuit': true, 'allowTernary': true }],
    eqeqeq: ['error', 'always', { null: 'ignore' }],
    'react-hooks/rules-of-hooks': 'error',
    'import/newline-after-import': 'error',
  },
  overrides: [
    {
      // enable the rule specifically for TypeScript files
      files: ['*.ts', '*.tsx'],
      rules: {
        '@typescript-eslint/explicit-function-return-type': 'off',
      },
    },
  ],
  env: {
    node: true,
    browser: true,
    es6: true,
    jest: true,
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
};
