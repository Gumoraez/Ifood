import React, { useEffect, useState } from 'react';
import { SafeAreaView, View, Text, TextInput, Button, FlatList, Alert, StyleSheet } from 'react-native';

const API_BASE = 'http://127.0.0.1:5000';

export default function App() {
  const [restaurants, setRestaurants] = useState([]);
  const [form, setForm] = useState({ id: null, owner_id: 1, name: '', address: '', category: '' });
  const [loading, setLoading] = useState(false);

  const loadRestaurants = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/restaurants`);
      const data = await resp.json();
      setRestaurants(Array.isArray(data) ? data : []);
    } catch (e) {
      Alert.alert('Erro', 'Falha ao carregar restaurantes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRestaurants();
  }, []);

  const createRestaurant = async () => {
    try {
      const payload = { owner_id: form.owner_id, name: form.name, address: form.address, category: form.category };
      const resp = await fetch(`${API_BASE}/api/restaurants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error('Erro ao criar');
      await loadRestaurants();
      setForm({ id: null, owner_id: 1, name: '', address: '', category: '' });
    } catch (e) {
      Alert.alert('Erro', 'Não foi possível criar o restaurante');
    }
  };

  const updateRestaurant = async () => {
    if (!form.id) return Alert.alert('Atenção', 'Selecione um restaurante antes de atualizar');
    try {
      const payload = { name: form.name, address: form.address, category: form.category };
      const resp = await fetch(`${API_BASE}/api/restaurants/${form.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error('Erro ao atualizar');
      await loadRestaurants();
      setForm({ id: null, owner_id: 1, name: '', address: '', category: '' });
    } catch (e) {
      Alert.alert('Erro', 'Não foi possível atualizar');
    }
  };

  const deleteRestaurant = async (id) => {
    try {
      const resp = await fetch(`${API_BASE}/api/restaurants/${id}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error('Erro ao excluir');
      await loadRestaurants();
    } catch (e) {
      Alert.alert('Erro', 'Não foi possível excluir');
    }
  };

  const selectRestaurant = (item) => {
    setForm({ id: item.id, owner_id: item.owner_id, name: item.name || '', address: item.address || '', category: item.category || '' });
  };

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <Text style={styles.title}>{item.name}</Text>
      <Text>{item.category} • {item.address}</Text>
      <View style={styles.row}>
        <Button title="Selecionar" onPress={() => selectRestaurant(item)} />
        <View style={{ width: 12 }} />
        <Button color="#c00" title="Excluir" onPress={() => deleteRestaurant(item.id)} />
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.header}>CRUD de Restaurantes</Text>
      <View style={styles.form}>
        <TextInput style={styles.input} placeholder="Nome" value={form.name} onChangeText={(t) => setForm({ ...form, name: t })} />
        <TextInput style={styles.input} placeholder="Endereço" value={form.address} onChangeText={(t) => setForm({ ...form, address: t })} />
        <TextInput style={styles.input} placeholder="Categoria" value={form.category} onChangeText={(t) => setForm({ ...form, category: t })} />
        <View style={styles.row}>
          <Button title="Criar" onPress={createRestaurant} />
          <View style={{ width: 12 }} />
          <Button title="Atualizar" onPress={updateRestaurant} />
        </View>
      </View>
      <Text style={styles.subHeader}>{loading ? 'Carregando...' : 'Lista de Restaurantes'}</Text>
      <FlatList data={restaurants} keyExtractor={(item) => String(item.id)} renderItem={renderItem} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  header: { fontSize: 22, fontWeight: 'bold', marginBottom: 12 },
  subHeader: { fontSize: 16, marginVertical: 8 },
  form: { marginBottom: 16 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 6, padding: 8, marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center' },
  card: { padding: 12, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, marginBottom: 8 },
  title: { fontSize: 16, fontWeight: '600' },
});