# 🛠️ Troubleshooting

## General principles

1. All Protein code must be valid YAML.
2. The YAML parser/renderer is its own validating tool for the language.
3. Exceptions produced are subclasses of `util.GeneralProteinError`.
   When possible, they provide the line number in the source code.

## Errors Checklist
1. **YAML Syntax Error**: This is by far the most common error. Invalid YAML can cause preprocessing failures. Validate YAML syntax and directive structure.  
    * Do not forget to add a colon (`:`) after a key,
      when the value is on the following lines.
1. **Incorrect keywords**: A Protein keyword is a YAML key that starts a construct.
   All keywords must start with a dot (`.`), e.g. : `.if`.<br>Any unknown keyword,
   or key not starting with a dot will be ignored.
4. **Unquoted Jinja expressions**: A Protein file must be a valid YAML file. It means that values
  that contain a Jinja expression **must** be quoted: 
    - ❌ Incorrect: `message: Hello, {{ name }}!`
    - ✅ Correct: `message:"Hello, {{ name }}!"`
2. **Undefined Variables**: A variable used in an expression is not defined in the current context or scope. Ensure all variables are declared within `.local` or passed correctly.  
3. **Duplicate keys**: A mapping (dictionary) can have only one key of each type.
   If a key is repeated, the parser will raise an error.
   If you are using the same key two times or more, it's likely that you should
   use a sequence (list) of mappings instead of a mapping.
   [This is principle applicable to YAML in general.]
3. **Missing Functions or Modules**: Occurs if a referenced function or module is not imported or defined. Verify `.module` imports and `.function` definitions.  
4. **Argument Mismatches**: When calling functions, ensure the number and order of arguments match the `.args` definition.
5. **Incorrect Expression Syntax**: Jinja2 expressions must be properly formatted. Check for missing braces, quotes, or invalid operations.  

## Debugging Tips
- Check error messages carefully for line numbers (in the YAML file) and hints 
- Use minimal examples to isolate issues  
- Add Jinja variables that use variables defined in `.local` to print intermediate values  
- Validate YAML files with external linters   