<script setup lang="ts">
import { computed } from 'vue';

import { storageUrl } from '@/composables/useStorageUrl';
import { attrNumber, attrString, type JSONContent, type JSONMark } from '@/types/content';

/**
 * 只读富文本渲染：白名单节点逐层渲染，未知节点仅保留子节点。
 * 全程使用插值，不注入 HTML，避免 XSS。
 */
const props = defineProps<{ node: JSONContent }>();

const children = computed(() => props.node.content ?? []);
const marks = computed<JSONMark[]>(() => props.node.marks ?? []);
const markTypes = computed(() => new Set(marks.value.map((mark) => mark.type)));

const linkHref = computed(() => {
  const href = marks.value.find((mark) => mark.type === 'link')?.attrs?.href;
  return typeof href === 'string' && /^https?:\/\//i.test(href) ? href : null;
});

const markClasses = computed(() => ({
  'rt-bold': markTypes.value.has('bold'),
  'rt-italic': markTypes.value.has('italic'),
  'rt-strike': markTypes.value.has('strike'),
  'rt-underline': markTypes.value.has('underline'),
  'rt-inline-code': markTypes.value.has('code'),
}));

const headingLevel = computed(() => Math.min(Math.max(attrNumber(props.node, 'level', 2), 1), 6));
const listStart = computed(() => attrNumber(props.node, 'start', 1));
const imageSrc = computed(() => attrString(props.node, 'src'));
const imageAlt = computed(() => attrString(props.node, 'alt') ?? '');
const imageTitle = computed(() => attrString(props.node, 'title'));
const videoSrc = computed(() => attrString(props.node, 'src'));
const videoPoster = computed(() => attrString(props.node, 'poster'));

function collectText(node: JSONContent): string {
  const own = node.text ?? '';
  return own + (node.content ?? []).map(collectText).join('');
}
</script>

<template>
  <!-- 文本 -->
  <template v-if="node.type === 'text'">
    <a
      v-if="linkHref"
      :href="linkHref"
      target="_blank"
      rel="noopener noreferrer nofollow"
      :class="markClasses"
      >{{ node.text }}</a
    >
    <span v-else :class="markClasses">{{ node.text }}</span>
  </template>

  <!-- 容器 -->
  <template v-else-if="node.type === 'doc'">
    <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
  </template>

  <p v-else-if="node.type === 'paragraph'" class="rt-paragraph">
    <template v-if="children.length">
      <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
    </template>
    <br v-else />
  </p>

  <component :is="`h${headingLevel}`" v-else-if="node.type === 'heading'" class="rt-heading">
    <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
  </component>

  <ul v-else-if="node.type === 'bulletList'" class="rt-list">
    <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
  </ul>

  <ol v-else-if="node.type === 'orderedList'" class="rt-list" :start="listStart">
    <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
  </ol>

  <li v-else-if="node.type === 'listItem'">
    <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
  </li>

  <blockquote v-else-if="node.type === 'blockquote'" class="rt-quote">
    <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
  </blockquote>

  <pre
    v-else-if="node.type === 'codeBlock'"
    class="rt-code-block"
  ><code>{{ collectText(node) }}</code></pre>

  <hr v-else-if="node.type === 'horizontalRule'" class="rt-rule" />

  <br v-else-if="node.type === 'hardBreak'" />

  <figure v-else-if="node.type === 'image' && imageSrc" class="rt-figure">
    <img
      :src="storageUrl(imageSrc)"
      :alt="imageAlt"
      :title="imageTitle ?? undefined"
      loading="lazy"
    />
    <figcaption v-if="imageTitle">{{ imageTitle }}</figcaption>
  </figure>

  <figure v-else-if="node.type === 'video' && videoSrc" class="rt-figure rt-video">
    <video
      :src="storageUrl(videoSrc)"
      :poster="videoPoster ? storageUrl(videoPoster) : undefined"
      controls
      preload="metadata"
      playsinline
    ></video>
  </figure>

  <!-- 未知节点：只渲染子节点，不输出原始 HTML -->
  <template v-else-if="children.length">
    <RichTextRenderer v-for="(child, index) in children" :key="index" :node="child" />
  </template>
</template>
