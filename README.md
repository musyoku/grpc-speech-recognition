## 動作環境

- Python 3

## 準備

### ライブラリのインストール

```
pip install google gcloud google-auth google-cloud-speech grpc-google-cloud-speech-v1beta1
```

`google.protobuf`が見つからない場合は以下のように一度消してから入れるとうまくいくかもしれません。

```
pip uninstall protobuf
pip uninstall google
pip install protobuf
pip install google
```

### サービスアカウントキーの作成

すでにキーのjsonファイルを作成済みの場合この項目は不要です。

あらかじめ[Google Cloud PlatformのWebサイト上](https://console.cloud.google.com/apis/dashboard)でSpeech APIのプロジェクトを作成しておく必要があります。

[Cloud SDKをダウンロード](https://cloud.google.com/sdk/?hl=ja)し、展開したディレクトリに移動します。

```
./install.sh
```

`google-cloud-sdk/bin`ディレクトリを`PATH`に追加してから以下のコマンドを実行します。

```
gcloud init
```

リンクが開かない場合は表示されているURLを直接ブラウザに入力します。

ブラウザでの操作が完了するとターミナル上で作成済みのプロジェクトを選択する画面が表示されるので選択します。

Do you want to configure Google Compute Engine ?と聞かれますが`n`と入力します。

次にデフォルトのキーを作ります。

```
gcloud auth application-default login
```