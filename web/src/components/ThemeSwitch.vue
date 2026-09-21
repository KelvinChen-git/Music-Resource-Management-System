<template>
  <el-switch 
    v-model="isDark" 
    inline-prompt
    style="--el-switch-on-color: #333; --el-switch-off-color: #409EFF;"
    @change="toggleDark"
    class="theme-switch"
  >
    <template #inline-prompt>
      <el-icon v-if="isDark"><moon /></el-icon>
      <el-icon v-else><sunny /></el-icon>
    </template>
  </el-switch>
</template>

<script setup>
import { useDark, useToggle } from '@vueuse/core'
import { Moon, Sunny } from '@element-plus/icons-vue'

const isDark = useDark({
  selector: 'html',
  attribute: 'class',
  valueDark: 'dark',
  valueLight: ''
})
const toggleDark = useToggle(isDark)
</script>

<style scoped>
.theme-switch {
  margin: 0 10px;
}
</style> 