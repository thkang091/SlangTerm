import * as Localization from 'expo-localization';
import { I18n } from 'i18n-js';

// Define translation object type
type TranslationKeys = {
  welcome: string;
  search: string;
  noResults: string;
  searchPrompt: string;
  errorLoading: string;
  meaning: string;
  examples: string;
  similarTerms: string;
  tags: string;
  addNew: string;
  submit: string;
  cancel: string;
  profile: string;
  settings: string;
  logout: string;
}

// Set up translations
const translations: Record<string, TranslationKeys> = {
  en: {
    welcome: 'Welcome to Slang Dictionary',
    search: 'Search slang terms...',
    noResults: 'No results found',
    searchPrompt: 'Search for slang terms to see results',
    errorLoading: 'Failed to load. Please try again.',
    meaning: 'Meaning',
    examples: 'Examples',
    similarTerms: 'Similar Terms',
    tags: 'Tags',
    addNew: 'Add New Slang',
    submit: 'Submit',
    cancel: 'Cancel',
    profile: 'Profile',
    settings: 'Settings',
    logout: 'Logout',
  },
  es: {
    welcome: 'Bienvenido al Diccionario de Jergas',
    search: 'Buscar términos de jerga...',
    noResults: 'No se encontraron resultados',
    searchPrompt: 'Busca términos de jerga para ver resultados',
    errorLoading: 'Error al cargar. Inténtalo de nuevo.',
    meaning: 'Significado',
    examples: 'Ejemplos',
    similarTerms: 'Términos Similares',
    tags: 'Etiquetas',
    addNew: 'Añadir Nueva Jerga',
    submit: 'Enviar',
    cancel: 'Cancelar',
    profile: 'Perfil',
    settings: 'Configuración',
    logout: 'Cerrar Sesión',
  },
};

// Create i18n instance
const i18n = new I18n(translations);

// Set the locale based on device settings
i18n.locale = Localization.locale.split('-')[0]; // Use device's language
i18n.enableFallback = true; // Use english if a translation is missing

export default i18n;