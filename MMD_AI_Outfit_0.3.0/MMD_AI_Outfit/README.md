# MMD AI Outfit

MMD制作でキャラクターの体格情報をまとめ、衣装フィッティングに利用するためのBlenderアドオンです。

## 機能

- 対象MMDモデルのArmature登録
- MMD標準ボーンによるSkeleton測定
- SkeletonとBody ShapeをまとめるCharacter Profileの保存
- Armatureに関連づいた身体メッシュの自動検出とUIからの手動選択
- 身体メッシュの胸囲・ウエスト・ヒップ断面測定

Body Shapeを測定するときも、先にSkeletonを測定してCharacter Profileを更新します。測定値はBlender単位（BU）で、現在の`.blend`ファイル内に保存されます。

## インストール

1. Blenderのアドオン管理画面で、`MMD_AI_Outfit_0.3.0.zip`をディスクからインストールします。
2. アドオンを有効にします。
3. 3Dビューポートで`N`を押し、`MMD AI Outfit`タブを開きます。

## 使い方

1. MMDモデルのArmature、またはそのArmatureで変形するメッシュを選んで「対象モデルとして登録」を押します。
2. 自動検出された身体メッシュを確認します。衣装などが選ばれた場合は、身体メッシュ欄から手動で選び直します。
3. 「Skeletonを測定」でSkeleton情報だけを更新できます。
4. 「Body Shapeを測定」を押すと、Skeletonを先に更新してから胸囲・ウエスト・ヒップの断面を測り、Character Profileに保存します。
5. `.blend`ファイルを保存すると、Profileも保存されます。

身体メッシュの自動検出はArmature modifierまたは親子関係を使います。自動検出結果が不適切なモデルでは、身体メッシュ欄から手動で指定してください。
