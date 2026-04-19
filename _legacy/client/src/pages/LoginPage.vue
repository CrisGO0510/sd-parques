<template>
  <q-page class="flex flex-center">
    <q-card style="min-width: 350px">
      <q-card-section>
        <div class="text-h5 text-center">Parques Distribuido</div>
      </q-card-section>
      <q-card-section>
        <q-form @submit="onSubmit">
          <q-input v-model="username" label="Usuario" outlined class="q-mb-md"
            :rules="[val => val.length >= 3 || 'Minimo 3 caracteres']" />
          <q-input v-model="password" label="Contrasena" type="password" outlined class="q-mb-md"
            :rules="[val => val.length >= 4 || 'Minimo 4 caracteres']" />
          <q-btn :label="isLogin ? 'Ingresar' : 'Registrarse'" type="submit" color="primary"
            class="full-width q-mb-sm" :loading="loading" />
          <q-btn :label="isLogin ? 'Crear cuenta' : 'Ya tengo cuenta'" flat class="full-width"
            @click="isLogin = !isLogin" />
        </q-form>
      </q-card-section>
      <q-card-section v-if="error">
        <q-banner class="bg-negative text-white">{{ error }}</q-banner>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from 'src/composables/useAuth'

const router = useRouter()
const { login, register } = useAuth()

const username = ref('')
const password = ref('')
const isLogin = ref(true)
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  loading.value = true
  error.value = ''
  try {
    if (isLogin.value) {
      await login(username.value, password.value)
    } else {
      await register(username.value, password.value)
      await login(username.value, password.value)
    }
    router.push('/lobby')
  } catch (e) {
    error.value = e.response?.data?.error || 'Error de conexion'
  } finally {
    loading.value = false
  }
}
</script>
