# File to COG

```bash
export DOCKER_TAG=file-to-cog

$(aws ecr get-login --no-include-email --region us-east-1)
# aws ecr create-repository --repository-name ${DOCKER_TAG}

docker build -t ${DOCKER_TAG} \
  --build-arg AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  --build-arg AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  -f Dockerfile .

docker tag ${DOCKER_TAG}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/${DOCKER_TAG}:latest

docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/${DOCKER_TAG}:latest

# Test it out
docker run ${DOCKER_TAG} 's3://cumulus-map-internal/file-staging/aimee/Polarimetric_height_profile_1577___1/rabi-tomo-fourier-hh.h5'
docker run ${DOCKER_TAG} 's3://cumulus-map-internal/file-staging/aimee/AfriSAR_KingAir_B200_flight_tracks_Gabon___1/traj57438_LVIS_SHP.zip'
docker run ${DOCKER_TAG} 's3://cumulus-map-internal/file-staging/aimee/user-added_testing___001/outfile.tif'
```
