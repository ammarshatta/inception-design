<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col gap-4 p-5">
    <p v-if="me.loading" class="text-base text-ink-gray-5">{{ __('جاري التحميل…') }}</p>
    <template v-else-if="me.data">
      <span v-if="me.data.branding.office_name" class="text-sm text-ink-gray-5">
        {{ me.data.branding.office_name }}
      </span>
      <h1 data-testid="greeting" class="text-2xl font-bold">
        {{ __('أهلاً، {0}', [me.data.full_name]) }}
      </h1>
    </template>
  </main>
</template>

<script setup lang="ts">
import { me } from '@/data/me'

me.fetch()
</script>
