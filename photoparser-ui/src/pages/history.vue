<template>
    <v-container>
        <v-data-table-server :items="history" @update:options="getFilesList" :items-length="total" class="mt-3">
        </v-data-table-server>
    </v-container>
</template>
  
<script>
import axios from 'axios';
export default {
  data() {
    return {
      headers: [
        {
          title: 'Query',
          align: 'start',
          sortable: false,
          key: 'search_query',
        },
        {
          title: 'pages',
          key: 'pages',
        },
        {
          title: 'language',
          key: 'language',
        },
      ],
      history: [],
      total: 0
    };
  },
  methods: {
    async getHistory() {
      try {
        const result = await axios.get('/api/photoparser/search_query/?skip=0&limit=100', {
          headers: { Authorization: `Bearer ${localStorage.getItem('access-token')}` }
        });
        console.log(result);
        this.history = result.data.result;
        this.total = result.data.total;
        console.log(this.history);
      } catch(e) {
        alert('error');
        console.error(e);
      }
    }
  },
  async mounted() {
    await this.getHistory();
  }
}
</script>