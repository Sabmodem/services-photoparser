<template>
  <v-app>
    <v-app-bar>
      <v-app-bar-title>photoparserx</v-app-bar-title>
      <template #append>
        <v-tabs>
          <v-tab to="/">search</v-tab>
          <v-tab to="/history">history</v-tab>
        </v-tabs>
      </template>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup>
  //
</script>
