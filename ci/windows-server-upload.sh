#!/usr/bin/env bash
pacman -S --noconfirm git rsync openssl

if [ ! -d ~/.ssh ]; then
  mkdir ~/.ssh
fi
printf "%s" "$UBUNTU_UPLOAD_KEY" > ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_rsa

echo -e "Host $1\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config
rsync_options=(-avh)
if [ -n "$UPLOAD_IGNORE_EXISTING" ]; then
  rsync_options+=(--ignore-existing)
fi
echo "copying $3 from $2 to root@$1:/web/downloads/$4"
rsync "${rsync_options[@]}" -e "ssh -p 2458" --include="*/" --include="$3" --exclude="*" "$2/" "root@$1:/web/downloads/$4"
