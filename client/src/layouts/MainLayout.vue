<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary">
      <q-toolbar>
        <q-toolbar-title>Parqués</q-toolbar-title>
        <q-space />
        <q-icon v-if="conn.status === ConnectionStatus.CONNECTED" name="wifi" />
        <q-icon v-else name="wifi_off" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ConnectionStatus, useConnectionStore } from 'src/stores/connection';
import { useAppEventSync } from 'src/composables/useAppEventSync';

const conn = useConnectionStore();

// MainLayout never unmounts during navigation, so it's the right place to
// own server-event handlers that must not miss an event between page
// transitions. Pages keep their navigation handlers on top.
useAppEventSync();
</script>
