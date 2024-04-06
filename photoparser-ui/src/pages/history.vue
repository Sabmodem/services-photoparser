<template>
    <v-container>
        <v-data-table-server :items="history" :headers="headers" @update:options="getFilesList" class="mt-3">
        <template v-slot:top>
            <v-toolbar flat>
            <v-toolbar-title>доступные файлы</v-toolbar-title>
            <v-dialog v-model="dialogDelete" max-width="500px">
                <v-card>
                <v-card-title class="text-h5">Удалить файл?</v-card-title>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="blue-darken-1" variant="text" @click="closeDelete">Нет</v-btn>
                    <v-btn color="blue-darken-1" variant="text" @click="deleteItemConfirm">Да</v-btn>
                    <v-spacer></v-spacer>
                </v-card-actions>
                </v-card>
            </v-dialog>
            </v-toolbar>
        </template>
        <template v-slot:item.actions="{ item }">
            <v-icon size="small" @click="deleteItem(item)">
            mdi-delete
            </v-icon>
        </template>
        </v-data-table-server>
    </v-container>
</template>
  
<script>
import axios from 'axios';
export default {
  data() {
    return {
      history: [],
      headers: [
        { title: 'название', key: 'filename' },
        { title: 'действия', key: 'actions', sortable: false },
      ],
      dialogDelete: false,
    };
  },
  methods: {
    deleteItem (item) {
      this.editedIndex = this.history.indexOf(item);
      this.editedItem = Object.assign({}, item);
      this.dialogDelete = true;
    },

    async deleteItemConfirm () {
      await ai.delete(`/api/filestorage/files/${this.history[this.editedIndex].filename}`);
      await this.getFilesList();
      this.history.splice(this.editedIndex, 1);
      this.closeDelete();
    },

    closeDelete () {
      this.dialogDelete = false;
      this.$nextTick(() => {
        this.editedItem = Object.assign({}, this.defaultItem);
        this.editedIndex = -1;
      })
    },

    async getFilesList() {
      const history = await ai.get('/api/filestorage/files');
      this.history = history.data;
    },
  }
}
</script>