<script setup lang="ts">
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { confirmState, settleConfirm } from '@/composables/useConfirm';
</script>

<template>
  <Dialog :open="confirmState.open" @update:open="(open) => !open && settleConfirm(false)">
    <DialogContent :show-close-button="false">
      <DialogHeader>
        <DialogTitle>{{ confirmState.title }}</DialogTitle>
        <DialogDescription v-if="confirmState.message">
          {{ confirmState.message }}
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" @click="settleConfirm(false)">取消</Button>
        <Button
          :variant="confirmState.danger ? 'destructive' : 'default'"
          @click="settleConfirm(true)"
        >
          {{ confirmState.confirmText }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
