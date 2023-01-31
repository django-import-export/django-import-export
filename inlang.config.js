// init the inlang.config
/**
 * @type {import("@inlang/core/config").DefineConfig}
 */
export async function defineConfig(env) {
  // import the Plugin which parse the translation file to inlang.com/editor/{yourRepo}
  const plugin = await env.$import(
    "https://cdn.jsdelivr.net/gh/jannesblobel/inlang-plugin-po@1/dist/index.js"
  );

  const pluginConfig = {
    // pathPattern is the location where your po files are stored
    // language is eqaul to language code
    pathPattern: "./import_export/locale/{language}/LC_MESSAGES/django.po",
    // referenceResorucePath is ony nesseassry, if you use an pot file
    /* @example 
    If you have a pot file it could like like 
    referenceResourcePath: "locale/reference.pot"
    If you DON'T use a pot file is referenceResources: null 
    */
    referenceResourcePath: null,
  };

  return {
    // referenceLanguage is the language code of your msgID mostly it is en
    referenceLanguage: "en",
    // languages are all languages stored in the "locale". You have to define this path in getLanguages
    languages: await getLanguages(env),
    readResources: (args) =>
      plugin.readResources({ ...args, ...env, pluginConfig }),
    writeResources: (args) =>
      plugin.writeResources({ ...args, ...env, pluginConfig }),
  };
}

// /**
//  * Automatically derives the languages in this repository.
//  */
async function getLanguages(env) {
  // translationsStoredIn is the place where the languages are stored
  // @example translationsStoredIn = "./translations/" don't forget the / at the end of a path
  const translationsStoredIn = "./import_export/locale/";

  //get all folders/files which are stored in the translationsStoredIn
  const files = await env.$fs.readdir(translationsStoredIn);

  const languages = [];
  // Search all folders in "translationsStoredIn" for po files
  // and pushing the matching languagecodes into the "languages" array
  for (const language of files) {
    try {
      const file = await env.$fs.readdir(
        translationsStoredIn + language + "/LC_MESSAGES/"
      );
      // Filtering the Po data in nested folders in case there is more than 1 file in them. @example messages.mo and messages.po
      for (const _file of file) {
        if (_file.endsWith(".po")) {
          languages.push(language);
        }
      }
    } catch (error) {}
  }
  return languages;
}
