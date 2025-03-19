import React, { useState, useEffect } from 'react';
import { StyleSheet, View, ScrollView, ActivityIndicator } from 'react-native';
import { Text, Card, Chip, Divider } from 'react-native-paper';
import { useLocalSearchParams } from 'expo-router';
import { getSlangDetails, type SlangTerm } from '../../api';
import i18n from '../../utils/translations';

export default function DetailsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [slang, setSlang] = useState<SlangTerm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSlangDetails = async () => {
      if (!id) return;
      
      try {
        const data = await getSlangDetails(parseInt(id));
        setSlang(data);
      } catch (err) {
        setError('Failed to load slang details.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSlangDetails();
  }, [id]);

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  if (!slang) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>Slang term not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.term}>{slang.term}</Text>
          
          <Divider style={styles.divider} />
          
          <Text style={styles.sectionTitle}>{i18n.t('meaning')}</Text>
          <Text style={styles.meaning}>{slang.meaning}</Text>
          
          {slang.examples && slang.examples.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>{i18n.t('examples')}</Text>
              {slang.examples.map((example, index) => (
                <Text key={index} style={styles.example}>• {example}</Text>
              ))}
            </>
          )}
          
          {slang.similar_terms && slang.similar_terms.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>{i18n.t('similarTerms')}</Text>
              <View style={styles.tagsContainer}>
                {slang.similar_terms.map((term, index) => (
                  <Chip key={index} style={styles.tag}>{term.term}</Chip>
                ))}
              </View>
            </>
          )}
          
          {slang.tags && slang.tags.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>{i18n.t('tags')}</Text>
              <View style={styles.tagsContainer}>
                {slang.tags.map((tag, index) => (
                  <Chip key={index} style={styles.tag}>{tag}</Chip>
                ))}
              </View>
            </>
          )}
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    margin: 16,
    borderRadius: 8,
  },
  term: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  divider: {
    marginVertical: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 16,
    marginBottom: 8,
  },
  meaning: {
    fontSize: 16,
    lineHeight: 24,
  },
  example: {
    fontSize: 16,
    fontStyle: 'italic',
    marginVertical: 4,
    paddingLeft: 8,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 4,
  },
  tag: {
    marginRight: 8,
    marginBottom: 8,
  },
  errorText: {
    textAlign: 'center',
    color: 'red',
    margin: 20,
    fontSize: 16,
  },
});