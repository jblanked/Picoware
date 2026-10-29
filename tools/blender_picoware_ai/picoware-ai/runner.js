// SPDX-License-Identifier: GPL-3.0-or-later
import * as THREE from './vendor/three.module.js';
import {GLTFExporter} from './vendor/GLTFExporter.js';

// This harness, not generated code, owns rendering, sampling and exporting.
window.runScene = async (options) => {
  const module = await import('./generated.js');
  if (typeof module.createScene !== 'function') throw Error('Export createScene({THREE, seed}).');
  const result = await module.createScene({THREE, seed: options.seed});
  if (!result || !(result.scene instanceof THREE.Scene)) throw Error('createScene must return {scene, update}.');
  const {scene, update} = result;
  if (options.animated && typeof update !== 'function') throw Error('Animated scenes require update(timeSeconds).');
  const apply = t => { if (update) update(t); scene.updateMatrixWorld(true); };
  apply(0);
  const nodes = [];
  scene.traverse(o => nodes.push(o));
  if (nodes.length > 2048) throw Error('Limit: 2048 objects.');
  let triangles = 0, meshCount = 0;
  const materials = new Map();
  const prefix = `AI_${options.job_id}_`;
  const names = {};
  nodes.forEach((o,i) => {
    names[prefix+i] = o.name || o.type;
    if (!o.visible) throw Error('Hidden objects are unsupported. Remove hidden objects or make the entire hierarchy visible before export.');
    if (o.isCamera || o.isLight) throw Error('Do not add cameras or lights; the helper supplies preview lighting.');
    if (o.isSkinnedMesh || o.isInstancedMesh || o.isLine || o.isPoints) throw Error('Use ordinary Mesh objects; no skins, instances, lines or points.');
    if (!o.isMesh) return;
    meshCount++;
    const g = o.geometry;
    if (!g.attributes.position || Object.keys(g.morphAttributes).length) throw Error('Use fixed mesh geometry without morph targets.');
    if (g.drawRange.start !== 0 || g.drawRange.count !== Infinity) throw Error('Partial or invalid geometry draw ranges are unsupported.');
    if (g.index && Array.from(g.index.array).some(i=>!Number.isInteger(i)||i<0||i>=g.attributes.position.count)) throw Error('Invalid geometry indices.');
    triangles += (g.index ? g.index.count : g.attributes.position.count) / 3;
    for (const a of Object.values(g.attributes)) {
      if (a.isInterleavedBufferAttribute) throw Error('Interleaved attributes are unsupported.');
      if (Array.from(a.array).some(x => !Number.isFinite(x))) throw Error('Non-finite geometry attribute.');
    }
    for (const m of (Array.isArray(o.material) ? o.material : [o.material])) {
      if (!m || (!m.isMeshStandardMaterial && !m.isMeshBasicMaterial)) throw Error('Use MeshStandardMaterial or MeshBasicMaterial with solid colors.');
      if (Object.values(m).some(v => v && v.isTexture) || m.vertexColors) throw Error('Textures and vertex colors are unsupported; use solid materials.');
      if (!materials.has(m)) materials.set(m, prefix+'material_'+materials.size);
    }
  });
  if (!meshCount || !Number.isInteger(triangles)) throw Error('Scene must contain complete mesh triangles.');
  if (triangles > 4096) throw Error(`Scene has ${triangles} triangles; reduce to at most 4096 (target ${options.triangle_target}).`);
  const structure = () => {
    const current=[]; scene.traverse(o=>current.push(o));
    if (current.length !== nodes.length || current.some((o,i)=>o!==nodes[i])) throw Error('Object hierarchy changes during animation.');
    if(nodes.some(o=>o.isMesh && (o.geometry.drawRange.start!==0 || o.geometry.drawRange.count!==Infinity)))
      throw Error('Changing geometry draw ranges is unsupported; keep complete fixed meshes.');
    if(nodes.some(o=>o.isMesh && (Object.keys(o.geometry.morphAttributes).length || o.morphTargetInfluences?.length)))
      throw Error('Morph targets and morph influences are unsupported, including those added during update(time). Animate object transforms instead.');
    return JSON.stringify(nodes.map(o=>({parent:o.parent?.uuid,visible:o.visible,
      geometry:o.isMesh ? {id:o.geometry.uuid,index:o.geometry.index?Array.from(o.geometry.index.array):null,
        attributes:Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),groups:o.geometry.groups,drawRange:o.geometry.drawRange} : null,
      material:o.isMesh?(Array.isArray(o.material)?o.material:[o.material]).map(m=>m.toJSON()):null})));
  };
  const baseline=structure();
  const transforms=()=>nodes.map(o=>{
    const v=[...o.position,...o.quaternion,...o.scale];
    if(v.some(x=>!Number.isFinite(x)||Math.abs(x)>1e12)) throw Error('Non-finite or excessive transform.');
    if(o.matrixAutoUpdate===false) throw Error('Use position/quaternion/scale, not manual matrices.');
    if(o===scene && v.some((x,i)=>x!==[0,0,0,0,0,0,1,1,1,1][i]))
      throw Error('Keep the Scene root transform at identity. Put meshes in a Group and animate that Group instead.');
    return v;
  });
  const first=transforms();
  const frames=options.animated ? Math.round(options.duration*options.fps) : 0;
  const times=[], samples=[];
  for(let f=0;f<=frames;f++) {
    const t=f/options.fps; apply(t);
    if(structure()!==baseline) throw Error('Changing geometry, visibility, hierarchy or materials is unsupported. Animate only object position, quaternion and scale.');
    times.push(t);samples.push(transforms());
  }
  // update(t) must be independent of prior calls, including reverse seeks.
  for (const i of [...new Set([0,Math.floor(frames/2),frames])]) {
    apply(times[i]);
    if(structure()!==baseline || JSON.stringify(transforms())!==JSON.stringify(samples[i])) throw Error('update(time) is not deterministic. Set absolute transforms from time; do not accumulate movement.');
  }
  apply(0);
  if(structure()!==baseline || JSON.stringify(transforms())!==JSON.stringify(first)) throw Error('update(0) does not reset the animation.');
  // Generated updates may look up objects/materials by their original names.
  // Assign unique export names only after the last call into generated code.
  nodes.forEach((o,i)=>{o.name=prefix+i;});
  materials.forEach((name,m)=>{m.name=name;});
  const tracks=[];
  if(options.animated) nodes.forEach((o,i)=>{
    for (const [property,start,end,Track] of [['position',0,3,THREE.VectorKeyframeTrack],['quaternion',3,7,THREE.QuaternionKeyframeTrack],['scale',7,10,THREE.VectorKeyframeTrack]]) {
      if(samples.some(s=>s[i].slice(start,end).some((x,k)=>x!==first[i][start+k])))
        tracks.push(new Track(o.name+'.'+property,times,samples.flatMap(s=>s[i].slice(start,end))));
    }
  });
  if(options.animated && !tracks.length) throw Error('Animated output requested but no object transforms move.');
  const clips=tracks.length?[new THREE.AnimationClip('Generated',frames/options.fps,tracks)]:[];
  // Camera and lighting belong to the preview only, not the exported asset.
  const data=await new GLTFExporter().parseAsync(scene,{binary:true,onlyVisible:true,animations:clips});
  // Validate the exported graph, not just the in-memory source scene. In
  // particular, every animation channel must target an exported node.
  const jsonSize=new DataView(data).getUint32(12,true);
  const gltf=JSON.parse(new TextDecoder().decode(new Uint8Array(data,20,jsonSize)));
  const exportedNodes=gltf.nodes || [];
  const exportedMeshes=exportedNodes.filter(n=>n.mesh!==undefined);
  if(exportedMeshes.length!==meshCount || !exportedMeshes.length)
    throw Error('Export dropped mesh objects; use a fully visible hierarchy of ordinary meshes.');
  let exportedTriangles=0;
  for(const node of exportedMeshes) for(const primitive of gltf.meshes[node.mesh].primitives) {
    if(primitive.mode!==undefined && primitive.mode!==4) throw Error('Export must contain triangle primitives.');
    const accessor=primitive.indices ?? primitive.attributes.POSITION;
    exportedTriangles+=gltf.accessors[accessor].count/3;
  }
  if(exportedTriangles!==triangles) throw Error('Export triangle count differs from the validated geometry; check geometry groups and material assignments.');
  const channels=(gltf.animations || []).flatMap(a=>a.channels);
  if(channels.length!==tracks.length || channels.some(c=>!Number.isInteger(c.target.node) || !exportedNodes[c.target.node]))
    throw Error('Export lost animation targets; every track must refer to an exported object.');
  const bounds=new THREE.Box3().setFromObject(scene);
  const center=bounds.getCenter(new THREE.Vector3());
  const span=Math.max(...bounds.getSize(new THREE.Vector3()).toArray());
  if(!Number.isFinite(span)||span<=0) throw Error('Invalid scene bounds.');
  const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
  renderer.setSize(800,600);renderer.setPixelRatio(1);
  document.body.replaceChildren(renderer.domElement);
  scene.background=new THREE.Color('#dbe6e9');
  scene.add(new THREE.HemisphereLight(0xffffff,0x64705b,2));
  const light=new THREE.DirectionalLight(0xffffff,3);light.position.copy(center).add(new THREE.Vector3(span,span*2,span));scene.add(light);
  const camera=new THREE.PerspectiveCamera(40,800/600,0.01,span*100);
  camera.position.copy(center).add(new THREE.Vector3(span*1.2,span,span*1.4));camera.lookAt(center);
  renderer.render(scene,camera);
  const materialReport={};
  materials.forEach((name,m)=>{materialReport[name]={rgba:[m.color.r,m.color.g,m.color.b,m.opacity],unlit:!!m.isMeshBasicMaterial};});
  const report={triangles,meshes:meshCount,tracks:tracks.length,duration:frames/options.fps,fps:options.fps,animated:options.animated,
    triangle_target:options.triangle_target,warnings:triangles>options.triangle_target?['Triangle target exceeded; below the 4096 hard limit.']:[],
    materials:materialReport,names,times,samples,node_names:nodes.map(o=>o.name)};
  // Transfer binary via base64 without a page-accessible filesystem bridge.
  let binary=''; for(const x of new Uint8Array(data)) binary+=String.fromCharCode(x);
  return {glb:btoa(binary),report};
};
