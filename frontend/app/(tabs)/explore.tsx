import React, { useState } from 'react';
import { StyleSheet, View, ScrollView } from 'react-native';
import { Text, TextInput, Button, Chip, Snackbar } from 'react-native-paper';
import { submitNewSlang } from '../../api';
import i18n from '../../utils/translations';

export default function AddScreen() {
  const [term, setTerm] = useState('');
  const [meaning, setMeaning] = useState('');
  const [examples, setExamples] = useState(['']);
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [snackbarVisible, setSnackbarVisible] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  const addExample = () => {
    setExamples([...examples, '']);
  };

  const updateExample = (text: string, index: number) => {
    const updatedExamples = [...examples];
    updatedExamples[index] = text;
    setExamples(updatedExamples);
  };

  const removeExample = (index: number) => {
    const updatedExamples = examples.filter((_, i) => i !== index);
    setExamples(updatedExamples);
  };

  const addTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleSubmit = async () => {
    if (!term.trim() || !meaning.trim()) {
      setSnackbarMessage('Term and meaning are required');
      setSnackbarVisible(true);
      return;
    }

    const filteredExamples = examples.filter(ex => ex.trim() !== '');

    const slangData = {
      term: term.trim(),
      meaning: meaning.trim(),
      examples: filteredExamples,
      tags: tags
    };

    setLoading(true);
    try {
      await submitNewSlang(slangData);
      setSnackbarMessage('Slang term submitted successfully!');
      
      // Reset form
      setTerm('');
      setMeaning('');
      setExamples(['']);
      setTags([]);
    } catch (error) {
      setSnackbarMessage('Failed to submit. Please try again.');
    } finally {
      setLoading(false);
      setSnackbarVisible(true);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.form}>
        <Text style={styles.title}>{i18n.t('addNew')}</Text>
        
        <TextInput
          label="Term *"
          value={term}
          onChangeText={setTerm}
          style={styles.input}
        />
        
        <TextInput
          label="Meaning *"
          value={meaning}
          onChangeText={setMeaning}
          multiline
          numberOfLines={4}
          style={styles.input}
        />
        
        <Text style={styles.sectionTitle}>Examples</Text>
        {examples.map((example, index) => (
          <View key={index} style={styles.exampleContainer}>
            <TextInput
              label={`Example ${index + 1}`}
              value={example}
              onChangeText={(text) => updateExample(text, index)}
              style={styles.exampleInput}
            />
            {examples.length > 1 && (
              <Button 
                icon="delete" 
                onPress={() => removeExample(index)}
                style={styles.removeButton}
              />
            )}
          </View>
        ))}
        
        <Button 
          mode="text" 
          onPress={addExample}
          icon="plus"
        >
          Add Example
        </Button>
        
        <Text style={styles.sectionTitle}>Tags</Text>
        <View style={styles.tagInputContainer}>
          <TextInput
            label="Add a tag"
            value={tagInput}
            onChangeText={setTagInput}
            style={styles.tagInput}
          />
          <Button 
            mode="contained" 
            onPress={addTag}
            disabled={!tagInput.trim()}
            style={styles.addTagButton}
          >
            Add
          </Button>
        </View>
        
        <View style={styles.tagsContainer}>
          {tags.map((tag, index) => (
            <Chip 
              key={index} 
              style={styles.tag}
              onClose={() => removeTag(tag)}
            >
              {tag}
            </Chip>
          ))}
        </View>
        
        <Button 
          mode="contained" 
          onPress={handleSubmit}
          loading={loading}
          style={styles.submitButton}
        >
          {i18n.t('submit')}
        </Button>
      </View>
      
      <Snackbar
        visible={snackbarVisible}
        onDismiss={() => setSnackbarVisible(false)}
        duration={3000}
      >
        {snackbarMessage}
      </Snackbar>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  form: {
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  input: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 16,
    marginBottom: 8,
  },
  exampleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  exampleInput: {
    flex: 1,
  },
  removeButton: {
    marginLeft: 8,
  },
  tagInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  tagInput: {
    flex: 1,
  },
  addTagButton: {
    marginLeft: 8,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 16,
  },
  tag: {
    marginRight: 8,
    marginBottom: 8,
  },
  submitButton: {
    marginTop: 16,
    paddingVertical: 8,
  },
});