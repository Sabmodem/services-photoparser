<template>
  <v-container fluid>
    <div class="d-flex flex-column align-center justify-center">
      <h1 class="pa-10">PhotoParserX</h1>
      <v-text-field label="Search images..." class="w-75" v-model="params.query_string" clearable>
        <template v-slot:append><v-icon icon="mdi mdi-search-web" size="x-large" @click="search"></v-icon></template>
      </v-text-field>
      <div class="d-flex flex-row w-100">
        <v-text-field label="pages" type="number" class="w-25 pa-3" v-model="params.pages"></v-text-field>
        <v-combobox label="time range" item-title="name" item-value="value" :items="timeRange" class="w-25 pa-3" v-model="params.time_range"></v-combobox>
        <v-combobox label="language" item-title="name" item-value="value" :items="language" class="w-25 pa-3" v-model="params.language"></v-combobox>
        <v-combobox label="safe search" item-title="name" item-value="value" :items="safeSearch" class="w-25 pa-3" v-model="params.safe_search"></v-combobox>
      </div>
      <div class="pa-10 d-flex flex-column align-center justify-center">
        <h2>search images</h2>
        <p>fast, cheap, high quality</p>
      </div>
    </div>
  </v-container>
</template>

<script>
import axios from 'axios';
import language from '../assets/language.json';
import timeRange from '../assets/timeRange.json';
import safeSearch from '../assets/safeSearch.json';
export default {
  data() {
    return {
      language,
      timeRange,
      safeSearch,
      params: {}
    }
  },
  methods: {
    async search () {
      try {
        const searchParams = {
          query_string: this.params.query_string,
          language: this.params.language.value,
          safe_search: this.params.safe_search.value,
          time_range: this.params.time_range.value,
          pages: this.params.pages
        };

        await axios.post('/api/photoparser/search_query/', searchParams, {
          headers: { Authorization: `Bearer ${localStorage.getItem('access-token')}` }
        });
        alert('fine!');
      } catch(e) {
        alert('error');
        console.error(e);
      }
    }
  }
}
</script>